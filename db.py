"""
db.py — Cliente centralizado de Supabase
Portal Docente APACUANA

Este módulo provee acceso directo a la API de Supabase (sin pasar por Flask-SQLAlchemy).
Útil para consultas, inserciones y modificaciones de datos desde scripts locales
antes de subir cambios al repositorio.

Clientes disponibles:
  - supabase       → usa SUPABASE_ANON_KEY  (respeta RLS, para operaciones normales)
  - supabase_admin → usa SUPABASE_SERVICE_ROLE_KEY (bypass RLS, para migraciones/admin)

Uso:
    from db import supabase, supabase_admin

    # Leer todos los registros
    resp = supabase.table("registros_asistencia").select("*").execute()
    print(resp.data)

    # Insertar un registro (con privilegios admin)
    supabase_admin.table("calificaciones").insert({...}).execute()
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carga las variables desde .env (solo tiene efecto en desarrollo local;
# en produccion (Render) las variables ya estan inyectadas por el entorno)
load_dotenv()

# ── Credenciales ──────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Validacion rapida al importar el modulo
if not SUPABASE_URL:
    raise ValueError(
        "[db.py] Falta SUPABASE_URL en el archivo .env. "
        "Revisa que el archivo .env exista en la raiz del proyecto."
    )
if not SUPABASE_ANON_KEY:
    raise ValueError(
        "[db.py] Falta SUPABASE_ANON_KEY en el archivo .env."
    )
if not SUPABASE_SERVICE_ROLE_KEY:
    print("[db.py] ADVERTENCIA: Falta SUPABASE_SERVICE_ROLE_KEY. supabase_admin usará la ANON_KEY como fallback.")
    SUPABASE_SERVICE_ROLE_KEY = SUPABASE_ANON_KEY

# ── Clientes Supabase ─────────────────────────────────────────────────────────

# Cliente estándar: respeta las Row Level Security (RLS) policies de Supabase.
# Usar para operaciones normales de lectura/escritura como lo haría el frontend.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Cliente administrador: bypasea RLS. Usar con cuidado, solo para scripts de
# migración, seeds, correcciones administrativas o tareas de mantenimiento.
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ── Verificacion de Conexion (solo al ejecutar directamente: python db.py) ────
if __name__ == "__main__":
    print("=" * 60)
    print("  Portal Docente APACUANA — Verificacion de conexion a Supabase")
    print("=" * 60)
    print(f"  URL:  {SUPABASE_URL}")
    print(f"  Anon key: {SUPABASE_ANON_KEY[:30]}...")
    print(f"  Service role key: {SUPABASE_SERVICE_ROLE_KEY[:30]}...")
    print()

    try:
        # Intenta listar las tablas publicas del schema para confirmar conexion
        # (usa admin para evitar restricciones RLS en información de schema)
        resp = supabase_admin.rpc("version").execute()
        print(f"  [OK] Conexion exitosa al proyecto Supabase.")
        print(f"       Respuesta: {resp}")
    except Exception as e:
        # Si la RPC 'version' no existe, igual confirma que el cliente funciona
        # con la estructura de error de Supabase (no es un error de red/auth)
        err_str = str(e)
        if "PGRST202" in err_str or "Could not find" in err_str or "function" in err_str.lower():
            print("  [OK] Conexion exitosa. (La funcion RPC 'version' no existe en este proyecto,")
            print("       pero la autenticacion con Supabase fue aceptada correctamente.)")
        else:
            print(f"  [ERROR] No se pudo conectar a Supabase:")
            print(f"          {err_str}")
            print()
            print("  Revisa:")
            print("    1. Que el archivo .env tenga las keys correctas")
            print("    2. Que tengas conexion a internet")
            print("    3. Que el proyecto en Supabase este activo (no pausado)")
    print("=" * 60)
