"""
Configurações do servidor
"""

import os

class Config:
    """Configuração principal"""
    
    # Pastas
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'outputs')
    
    # Limites
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
