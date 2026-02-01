"""
Servidor Web para Motor de Transpilação Minecraft
API REST para conversão de mods Java → Bedrock
Versão 2.0 - Compatível com transpiler_engine v2
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from transpiler_engine import transpile_jar
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

# Importa a função principal do transpiler
from transpiler_engine import transpile_jar

# Configuração
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializa Flask
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app)

# Armazenamento de jobs em memória
conversion_jobs = {}

class ConversionJob:
    """Representa um job de conversão"""
    
    def __init__(self, job_id: str, filename: str):
        self.job_id = job_id
        self.filename = filename
        self.status = 'queued'
        self.progress = 0
        self.message = 'Aguardando processamento...'
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
# ROTAS DA API
# ============================================================================

@app.route('/')
def index():
    """Serve a página principal"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Endpoint para upload de arquivo JAR"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo inválido'}), 400
    
    if not file.filename.endswith('.jar'):
        return jsonify({'error': 'Apenas arquivos .jar são aceitos'}), 400
    
    # Validação de tamanho
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > app.config['MAX_FILE_SIZE']:
        return jsonify({
            'error': f'Arquivo muito grande. Máximo: {app.config["MAX_FILE_SIZE"] / (1024*1024):.0f}MB'
        }), 400
    
    # Gera ID único
    job_id = str(uuid.uuid4())
    
    # Salva arquivo
    filename = secure_filename(file.filename)
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    jar_path = upload_path / filename
    file.save(jar_path)
    
    logger.info(f"Upload: {filename} ({file_size / 1024:.2f} KB) - Job: {job_id}")
    
    # Cria job
    job = ConversionJob(job_id, filename)
    conversion_jobs[job_id] = job
    
    # Inicia conversão
    thread = threading.Thread(target=process_conversion, args=(job_id, jar_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'message': 'Upload realizado. Processamento iniciado.'
    }), 202

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Verifica status de um job"""
    
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    return jsonify(conversion_jobs[job_id].to_dict())

@app.route('/api/download/<job_id>', methods=['GET'])
def download_result(job_id):
    """Baixa o .mcaddon resultante"""
    
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = conversion_jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Conversão não concluída'}), 400
    
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
    """Lista jobs recentes"""
    
    jobs = sorted(
        conversion_jobs.values(),
        key=lambda x: x.started_at or datetime.min,
        reverse=True
    )[:50]
    
    return jsonify({
        'jobs': [job.to_dict() for job in jobs],
        'total': len(conversion_jobs)
    })

# ============================================================================
# PROCESSAMENTO
# ============================================================================

def process_conversion(job_id: str, jar_path: Path):
    """Processa conversão em background"""
    
    job = conversion_jobs[job_id]
    job.status = 'processing'
    job.started_at = datetime.now()
    job.progress = 10
    job.message = 'Iniciando análise do JAR...'
    
    output_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"Iniciando conversão - Job: {job_id}")
        
        # Atualiza progresso
        job.progress = 20
        job.message = 'Analisando estrutura do mod...'
        
        # CHAMA A FUNÇÃO PRINCIPAL
        result = transpile_jar(
            jar_path=str(jar_path),
            output_folder=str(output_dir)
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Erro desconhecido'))
        
        # Atualiza progresso
        job.progress = 90
        job.message = 'Finalizando...'
        
        # Localiza arquivo .mcaddon
        mcaddon_file = result.get('output_file')
        
        if not mcaddon_file or not os.path.exists(mcaddon_file):
            raise Exception('Arquivo .mcaddon não foi gerado')
        
        # Sucesso
        job.status = 'completed'
        job.progress = 100
        job.message = 'Conversão concluída!'
        job.result_file = mcaddon_file
        job.completed_at = datetime.now()
        job.stats = result.get('stats', {})
        
        logger.info(f"Conversão concluída - Job: {job_id}")
        
        # Agenda limpeza
        threading.Thread(
            target=cleanup_job,
            args=(job_id, 3600),
            daemon=True
        ).start()
        
    except Exception as e:
        logger.error(f"Erro - Job: {job_id} - {str(e)}", exc_info=True)
        
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Erro: {str(e)}'
        job.completed_at = datetime.now()
        
        # Limpa imediatamente
        threading.Thread(
            target=cleanup_job,
            args=(job_id, 60),
            daemon=True
        ).start()

def cleanup_job(job_id: str, delay: int):
    """Limpa arquivos temporários"""
    
    time.sleep(delay)
    logger.info(f"Limpando job: {job_id}")
    
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
    
    # Inicia servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # False em produção
    )
