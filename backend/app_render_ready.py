"""
Servidor Flask para Transpiler Minecraft
Versão Render-Ready com imports corrigidos
"""

import os
import sys
from pathlib import Path

# ✅ CORREÇÃO: Adiciona backend ao path ANTES de importar
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import shutil
import threading
import time
from datetime import datetime
import logging

# ✅ Agora o import funciona
try:
    from transpiler_engine import transpile_jar
    print("✅ transpiler_engine importado com sucesso")
except ImportError as e:
    print(f"❌ ERRO ao importar transpiler_engine: {e}")
    print(f"📁 Diretório atual: {os.getcwd()}")
    print(f"📂 Arquivos no diretório: {os.listdir('.')}")
    sys.exit(1)

# Configuração
try:
    from config import Config
except:
    # Fallback se config.py não existir
    class Config:
        UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
        OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'outputs')
        MAX_FILE_SIZE = 100 * 1024 * 1024
        SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
        CORS_ORIGINS = ['*']

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializa Flask
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app, origins='*')

# Jobs
conversion_jobs = {}

class ConversionJob:
    def __init__(self, job_id: str, filename: str):
        self.job_id = job_id
        self.filename = filename
        self.status = 'queued'
        self.progress = 0
        self.message = 'Aguardando...'
        self.result_file = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.stats = {}
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'filename': self.filename,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'result_file': self.result_file,
            'error': self.error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'stats': self.stats
        }

# ============================================================================
# ROTAS
# ============================================================================

@app.route('/')
def index():
    """Página principal"""
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except:
        return jsonify({
            'status': 'API Online',
            'version': '3.1',
            'endpoints': {
                'health': '/api/health',
                'upload': '/api/upload',
                'status': '/api/status/<job_id>',
                'download': '/api/download/<job_id>'
            }
        })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'version': '3.1',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/upload', methods=['POST'])
def upload():
    """Upload de JAR"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo'}), 400
    
    file = request.files['file']
    
    if not file.filename or not file.filename.endswith('.jar'):
        return jsonify({'error': 'Arquivo deve ser .jar'}), 400
    
    # Valida tamanho
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > app.config['MAX_FILE_SIZE']:
        return jsonify({'error': 'Arquivo muito grande'}), 400
    
    # Salva
    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    jar_path = upload_path / filename
    file.save(jar_path)
    
    logger.info(f"Upload: {filename} ({size/1024:.1f}KB) - Job: {job_id}")
    
    # Cria job
    job = ConversionJob(job_id, filename)
    conversion_jobs[job_id] = job
    
    # Inicia conversão
    thread = threading.Thread(target=process, args=(job_id, jar_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'message': 'Processamento iniciado'
    }), 202

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    """Status do job"""
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify(conversion_jobs[job_id].to_dict())

@app.route('/api/download/<job_id>', methods=['GET'])
def download(job_id):
    """Download do resultado"""
    
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = conversion_jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Ainda processando'}), 400
    
    if not job.result_file or not os.path.exists(job.result_file):
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    logger.info(f"Download: {job_id}")
    
    return send_file(
        job.result_file,
        as_attachment=True,
        download_name=Path(job.result_file).name,
        mimetype='application/zip'
    )

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """Lista jobs"""
    jobs = sorted(
        conversion_jobs.values(),
        key=lambda x: x.started_at or datetime.min,
        reverse=True
    )[:50]
    
    return jsonify({
        'jobs': [j.to_dict() for j in jobs],
        'total': len(conversion_jobs)
    })

# ============================================================================
# PROCESSAMENTO
# ============================================================================

def process(job_id: str, jar_path: Path):
    """Processa conversão"""
    
    job = conversion_jobs[job_id]
    job.status = 'processing'
    job.started_at = datetime.now()
    job.progress = 10
    job.message = 'Analisando JAR...'
    
    output_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"Processando: {job_id}")
        
        job.progress = 30
        job.message = 'Convertendo...'
        
        # ✅ Chama função principal
        result = transpile_jar(
            jar_path=str(jar_path),
            output_folder=str(output_dir)
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Erro desconhecido'))
        
        job.progress = 90
        job.message = 'Finalizando...'
        
        # Verifica arquivo
        mcaddon = result.get('output_file')
        if not mcaddon or not os.path.exists(mcaddon):
            raise Exception('Arquivo .mcaddon não gerado')
        
        # Sucesso
        job.status = 'completed'
        job.progress = 100
        job.message = 'Concluído!'
        job.result_file = mcaddon
        job.completed_at = datetime.now()
        job.stats = result.get('stats', {})
        
        logger.info(f"Concluído: {job_id}")
        
        # Limpa depois de 1h
        threading.Thread(target=cleanup, args=(job_id, 3600), daemon=True).start()
        
    except Exception as e:
        logger.error(f"Erro no job {job_id}: {e}", exc_info=True)
        
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Erro: {str(e)}'
        job.completed_at = datetime.now()
        
        # Limpa depois de 1min
        threading.Thread(target=cleanup, args=(job_id, 60), daemon=True).start()

def cleanup(job_id: str, delay: int):
    """Limpa arquivos temporários"""
    time.sleep(delay)
    
    logger.info(f"Limpando: {job_id}")
    
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    output_path = Path(app.config['OUTPUT_FOLDER']) / job_id
    
    for path in [upload_path, output_path]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    
    if job_id in conversion_jobs:
        del conversion_jobs[job_id]

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    # Cria pastas
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    # Porta
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"🚀 Servidor iniciando na porta {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
