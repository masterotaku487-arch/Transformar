"""
Servidor Web para Motor de Transpilação Minecraft
Versão 2.0 - Alta Performance & Threading
"""

import os
import uuid
import shutil
import threading
import time
import logging
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- GARANTIR IMPORTAÇÃO NO RENDER ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from transpiler_engine import transpile_jar
except ImportError as e:
    print(f"ERRO CRÍTICO: transpiler_engine.py não encontrado: {e}")

# --- CONFIGURAÇÃO ---
class Config:
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'converted'
    MAX_CONTENT_LENGTH = 128 * 1024 * 1024  # Suporta mods de até 128MB
    DEBUG = False

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app)

# Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Memória de Jobs
conversion_jobs = {}

class ConversionJob:
    def __init__(self, job_id, filename):
        self.job_id = job_id
        self.filename = filename
        self.status = 'processing'
        self.progress = 0
        self.message = 'Iniciando extração...'
        self.result_file = None
        self.error = None
        self.started_at = datetime.now()

# --- ROTAS ---

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Arquivo sem nome'}), 400

    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    # Prepara pastas
    job_dir = Path(app.config['UPLOAD_FOLDER']) / job_id
    out_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    jar_path = job_dir / filename
    file.save(jar_path)
    
    # Cria o Job e inicia a Thread
    job = ConversionJob(job_id, filename)
    conversion_jobs[job_id] = job
    
    thread = threading.Thread(target=run_conversion_task, args=(job_id, str(jar_path), str(out_dir)))
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'processing'})

def run_conversion_task(job_id, jar_path, out_dir):
    job = conversion_jobs.get(job_id)
    try:
        logger.info(f"Processando Job {job_id}...")
        
        # Executa o motor
        res_path = transpile_jar(jar_path, out_dir)
        
        job.status = 'completed'
        job.progress = 100
        job.result_file = res_path
        job.message = 'Pronto para baixar!'
        
    except Exception as e:
        logger.error(f"Falha no Job {job_id}: {str(e)}")
        job.status = 'failed'
        job.error = str(e)
        job.message = f"Erro: {str(e)}"

@app.route('/api/status/<job_id>')
def get_status(job_id):
    job = conversion_jobs.get(job_id)
    if not job: return jsonify({'error': 'Não encontrado'}), 404
    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'download_url': f'/api/download/{job_id}' if job.status == 'completed' else None
    })

@app.route('/api/download/<job_id>')
def download(job_id):
    job = conversion_jobs.get(job_id)
    if job and job.status == 'completed' and job.result_file:
        return send_file(job.result_file, as_attachment=True)
    return jsonify({'error': 'Não disponível'}), 404

# --- LIMPEZA AUTOMÁTICA (Background) ---
def auto_cleanup():
    while True:
        time.sleep(1800) # Checa a cada 30 min
        now = time.time()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            p = Path(folder)
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir() and (now - item.stat().st_mtime > 3600):
                        shutil.rmtree(item, ignore_errors=True)
                        logger.info(f"Limpeza: {item.name} removido.")

threading.Thread(target=auto_cleanup, daemon=True).start()

if __name__ == '__main__':
    Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
    Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
                         
