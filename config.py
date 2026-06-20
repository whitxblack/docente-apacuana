import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'flask-insecure-key')
    
    # Base de datos
    _database_url = os.environ.get('DATABASE_URL', '').strip()
    
    # Auto-corrección si la URL contiene '@@' (por contraseñas terminadas en '@')
    if '@@' in _database_url:
        _database_url = _database_url.replace('@@', '%40@', 1)
        
    # Limpiar pgbouncer y connection_limit sin dañar otros parámetros ni el nombre de la BD
    if '?' in _database_url:
        base_url, query_str = _database_url.split('?', 1)
        # Reconstruir parametros ignorando los exclusivos de Supabase que rompen psycopg2
        params = [p for p in query_str.split('&') if not p.startswith(('pgbouncer=', 'connection_limit='))]
        _database_url = base_url + ('?' + '&'.join(params) if params else '')
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
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
    SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '').strip()
