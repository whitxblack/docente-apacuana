import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'flask-insecure-key')
    
    # Base de datos
    _database_url = os.environ.get('DATABASE_URL', '')
    
    # Auto-corrección si la URL contiene '@@' (por contraseñas terminadas en '@')
    if '@@' in _database_url:
        _database_url = _database_url.replace('@@', '%40@', 1)
        
    if _database_url:
        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        # Fallback a la BD local de gestor-apacuana (SQLite) si no hay URL
        if os.environ.get('VERCEL'):
            SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/db.sqlite3'
        else:
            GESTOR_DIR = BASE_DIR.parent / 'gestor-apacuana'
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{GESTOR_DIR / 'db.sqlite3'}"
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Supabase Integracion
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
