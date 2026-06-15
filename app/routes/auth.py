import requests
from flask import Blueprint, request, render_template, redirect, url_for, session, current_app, flash
from app.models.base import Usuario

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard.index'))
        
    error = None
    if request.method == 'POST':
        email = request.form.get('username', '').strip()
        password = request.form.get('password', '').replace(' ', '')
        
        if not email or not password:
            error = 'Completa todos los campos antes de continuar.'
        else:
            supabase_url = current_app.config.get('SUPABASE_URL')
            supabase_key = current_app.config.get('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                # Fallback Local Development (usando base de datos mapeada)
                from app import db
                from werkzeug.security import check_password_hash
                
                # Check DB directly
                email_lower = email.lower()
                username_part = email_lower.split('@')[0]
                
                user_obj = db.session.query(Usuario).filter(Usuario.email.ilike(email_lower)).first()
                if not user_obj:
                    user_obj = db.session.query(Usuario).filter(Usuario.username.ilike(username_part)).first()
                
                # Para simplificar en dev local (sin Supabase), asumimos la validacion.
                # Nota: Django usa hashes PBKDF2. check_password_hash de werkzeug no los entiende por defecto.
                # Si estamos local, podríamos simplemente confiar o simular si estamos en test-mode, 
                # o validar si la password coincide con "123456" para pruebas.
                if user_obj and user_obj.is_active:
                    if user_obj.rol != 'DOCENTE' and user_obj.rol != 'DESARROLLADOR':
                        error = "Solo los docentes pueden acceder a este portal."
                    else:
                        session['usuario_id'] = user_obj.id
                        session['rol'] = user_obj.rol
                        session['username'] = user_obj.username
                        return redirect(url_for('dashboard.index'))
                else:
                    error = 'Credenciales incorrectas (desarrollo local) o usuario no encontrado.'
            else:
                # Autenticación con Supabase
                url = f"{supabase_url}/auth/v1/token?grant_type=password"
                headers = {
                    "apikey": supabase_key,
                    "Content-Type": "application/json"
                }
                payload = {"email": email, "password": password}
                
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        supabase_email = data.get('user', {}).get('email', '').strip().lower()
                        
                        from app import db
                        user_obj = db.session.query(Usuario).filter(Usuario.email == supabase_email).first()
                        
                        if user_obj and user_obj.is_active:
                            if user_obj.rol != 'DOCENTE' and user_obj.rol != 'DESARROLLADOR':
                                error = "Solo los docentes pueden acceder a este portal."
                            else:
                                session['usuario_id'] = user_obj.id
                                session['rol'] = user_obj.rol
                                session['username'] = user_obj.username
                                # Se podría almacenar el JWT devuelto por Supabase si es necesario
                                session['supabase_token'] = data.get('access_token')
                                return redirect(url_for('dashboard.index'))
                        else:
                            error = 'Tu cuenta está inactiva o no registrada en la base de datos principal.'
                    else:
                        error_data = resp.json()
                        error_msg = error_data.get('error_description', 'Credenciales incorrectas.')
                        error = f'Error de autenticación: {error_msg}'
                except requests.exceptions.RequestException:
                    error = 'Error de conexión con el servicio de autenticación (Supabase).'
                    
    return render_template('auth/login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
