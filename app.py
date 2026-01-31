"""
Servidor Web para Motor de Transpilação Minecraft
API REST para conversão de mods Java → Bedrock
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

# Importa o motor de transpilação
from transpiler_engine import AvaritiaTranspiler

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

# Armazenamento de jobs em memória (em produção, use Redis/DB)
conversion_jobs = {}

class ConversionJob:
    """Representa um job de conversão"""
    
    def __init__(self, job_id: str, filename: str):
        self.job_id = job_id
        self.filename = filename
        self.status = 'queued'  # queued, processing, completed, failed
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
        'version': '1.0.0'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Endpoint para upload de arquivo JAR
    
    Returns:
        JSON com job_id para acompanhamento
    """
    
    # Validação do arquivo
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
    
    # Gera ID único para o job
    job_id = str(uuid.uuid4())
    
    # Salva arquivo
    filename = secure_filename(file.filename)
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    jar_path = upload_path / filename
    file.save(jar_path)
    
    logger.info(f"Arquivo recebido: {filename} ({file_size / 1024:.2f} KB) - Job: {job_id}")
    
    # Cria job
    job = ConversionJob(job_id, filename)
    conversion_jobs[job_id] = job
    
    # Inicia conversão em background
    thread = threading.Thread(
        target=process_conversion,
        args=(job_id, jar_path)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'message': 'Upload realizado com sucesso. Processamento iniciado.'
    }), 202

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """
    Verifica status de um job de conversão
    
    Args:
        job_id: ID do job
    
    Returns:
        JSON com status e progresso
    """
    
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = conversion_jobs[job_id]
    return jsonify(job.to_dict())

@app.route('/api/download/<job_id>', methods=['GET'])
def download_result(job_id):
    """
    Baixa o arquivo .mcaddon resultante
    
    Args:
        job_id: ID do job
    
    Returns:
        Arquivo .mcaddon
    """
    
    if job_id not in conversion_jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = conversion_jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Conversão ainda não foi concluída'}), 400
    
    if not job.result_file or not os.path.exists(job.result_file):
        return jsonify({'error': 'Arquivo de resultado não encontrado'}), 404
    
    logger.info(f"Download iniciado - Job: {job_id}")
    
    return send_file(
        job.result_file,
        as_attachment=True,
        download_name=Path(job.result_file).name,
        mimetype='application/zip'
    )

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """Lista todos os jobs (últimos 50)"""
    
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
    """
    Processa a conversão em background
    
    Args:
        job_id: ID do job
        jar_path: Caminho do arquivo JAR
    """
    
    job = conversion_jobs[job_id]
    job.status = 'processing'
    job.started_at = datetime.now()
    job.progress = 10
    job.message = 'Iniciando análise do JAR...'
    
    output_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Extrai nome do mod
        mod_name = jar_path.stem.lower().split('-')[0]
        
        logger.info(f"Iniciando conversão - Job: {job_id}, Mod: {mod_name}")
        
        # Cria transpilador com callback de progresso
        transpiler = AvaritiaTranspiler(
            jar_path=str(jar_path),
            output_dir=str(output_dir),
            mod_name=mod_name
        )
        
        # Hook para atualizar progresso
        original_parse = transpiler.parse_jar
        original_convert = transpiler.convert_all
        original_scripts = transpiler.generate_scripts
        original_build = transpiler.build_addon_structure
        original_package = transpiler.package_mcaddon
        
        def parse_with_progress():
            job.progress = 20
            job.message = 'Analisando classes Java...'
            original_parse()
            job.progress = 40
        
        def convert_with_progress():
            job.message = 'Convertendo items e receitas...'
            original_convert()
            job.progress = 60
        
        def scripts_with_progress():
            job.message = 'Gerando scripts customizados...'
            original_scripts()
            job.progress = 75
        
        def build_with_progress():
            job.message = 'Montando estrutura do addon...'
            original_build()
            job.progress = 85
        
        def package_with_progress():
            job.message = 'Empacotando .mcaddon...'
            original_package()
            job.progress = 95
        
        transpiler.parse_jar = parse_with_progress
        transpiler.convert_all = convert_with_progress
        transpiler.generate_scripts = scripts_with_progress
        transpiler.build_addon_structure = build_with_progress
        transpiler.package_mcaddon = package_with_progress
        
        # Executa pipeline
        transpiler.run()
        
        # Localiza arquivo .mcaddon
        mcaddon_files = list(output_dir.glob('*.mcaddon'))
        
        if not mcaddon_files:
            raise Exception('Arquivo .mcaddon não foi gerado')
        
        result_file = mcaddon_files[0]
        
        # Atualiza job
        job.status = 'completed'
        job.progress = 100
        job.message = 'Conversão concluída com sucesso!'
        job.result_file = str(result_file)
        job.completed_at = datetime.now()
        job.stats = transpiler.stats
        
        logger.info(f"Conversão concluída - Job: {job_id}")
        
        # Agenda limpeza após 1 hora
        cleanup_thread = threading.Thread(
            target=cleanup_job,
            args=(job_id, 3600)
        )
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
    except Exception as e:
        logger.error(f"Erro na conversão - Job: {job_id} - {str(e)}", exc_info=True)
        
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Erro: {str(e)}'
        job.completed_at = datetime.now()
        
        # Limpa imediatamente em caso de erro
        cleanup_thread = threading.Thread(
            target=cleanup_job,
            args=(job_id, 60)
        )
        cleanup_thread.daemon = True
        cleanup_thread.start()

def cleanup_job(job_id: str, delay: int):
    """
    Limpa arquivos temporários de um job
    
    Args:
        job_id: ID do job
        delay: Tempo de espera em segundos
    """
    
    time.sleep(delay)
    
    logger.info(f"Limpando job: {job_id}")
    
    # Remove pastas
    upload_path = Path(app.config['UPLOAD_FOLDER']) / job_id
    output_path = Path(app.config['OUTPUT_FOLDER']) / job_id
    
    for path in [upload_path, output_path]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    
    # Remove do dicionário
    if job_id in conversion_jobs:
        del conversion_jobs[job_id]

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    # Cria pastas necessárias
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    # Inicia servidor
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
