"""
Servidor Web para Motor de Transpilação Minecraft
API REST para conversão de mods Java → Bedrock
Versão 2.0 - Totalmente Integrada
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime
import logging
import sys

# --- AJUSTE DE CAMINHO PARA O RENDER ---
# Garante que o Python encontre o transpiler_engine.py na mesma pasta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from transpiler_engine import transpile_jar
except ImportError as e:
    print(f"ERRO: Verifique se transpiler_engine.py esta na pasta backend: {e}")

# --- CONFIGURAÇÃO ---
class Config:
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'converted'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # Aumentado para 100MB
    DEBUG = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app)

# Armazenamento de jobs em memória
conversion_jobs = {}

class ConversionJob:
    def __init__(self, job_id, filename):
        self.job_id = job_id
        self.filename = filename
        self.status = 'processing'
        self.progress = 0
        self.message = 'Iniciando conversão...'
        self.result_file = None
        self.error = None
        self.started_at = datetime.now()

# --- ROTAS API ---

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo invalido'}), 400

    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    # Criar diretórios do Job
    job_upload_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    job_output_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    jar_path = job_upload_dir / filename
    file.save(jar_path)
    
    # Registrar o Job
    job = ConversionJob(job_id, filename)
    conversion_jobs[job_id] = job
    
    # Rodar conversão em uma thread separada para não travar o site
    thread = threading.Thread(target=process_conversion, args=(job_id, str(jar_path), str(job_output_dir)))
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Conversão iniciada em segundo plano'
    })

def process_conversion(job_id, jar_path, output_dir):
    job = conversion_jobs.get(job_id)
    try:
        logger.info(f"Iniciando conversão do Job: {job_id}")
        
        # Chama o motor que o Claude gerou
        result_path = transpile_jar(jar_path, output_dir)
        
        job.status = 'completed'
        job.progress = 100
        job.result_file = result_path
        job.message = 'Conversão concluída com sucesso!'
        logger.info(f"Job {job_id} finalizado.")
        
    except Exception as e:
        logger.error(f"Erro no Job {job_id}: {str(e)}")
        job.status = 'failed'
        job.error = str(e)
        job.message = f"Erro técnico: {str(e)}"

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = conversion_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'error': job.error,
        'download_url': f'/api/download/{job_id}' if job.status == 'completed' else None
    })

@app.route('/api/download/<job_id>', methods=['GET'])
def download(job_id):
    job = conversion_jobs.get(job_id)
    if job and job.status == 'completed' and job.result_file:
        return send_file(job.result_file, as_attachment=True)
    return jsonify({'error': 'Arquivo não disponível'}), 404

# --- LIMPEZA DE ARQUIVOS ANTIGOS ---
def cleanup_old_files():
    """Remove arquivos com mais de 1 hora para não lotar o Render"""
    while True:
        time.sleep(3600)
        now = time.time()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            p = Path(folder)
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir() and (now - item.stat().st_mtime > 3600):
                        shutil.rmtree(item)
                        logger.info(f"Limpeza: Removido {item}")

# Iniciar thread de limpeza
threading.Thread(target=cleanup_old_files, daemon=True).start()

if __name__ == '__main__':
    # Criar pastas iniciais
    Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
    Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
            
