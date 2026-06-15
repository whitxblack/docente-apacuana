from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        from app.models.base import init_models
        init_models()

    # Register blueprints (rutas)
    from app.routes.dashboard import dashboard_bp
    from app.routes.auth import auth_bp
    from app.routes.calificaciones import calificaciones_bp
    from app.routes.planificacion import planificacion_bp
    from app.routes.asistencia import asistencia_bp
    from app.routes.api_routes import api_bp
    from app.routes.planificacion_api import planificacion_api_bp
    from app.routes.asistencia_api import asistencia_api_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(calificaciones_bp)
    app.register_blueprint(planificacion_bp)
    app.register_blueprint(asistencia_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(planificacion_api_bp)
    app.register_blueprint(asistencia_api_bp)

    @app.route('/')
    def root():
        return redirect(url_for('auth.login'))

    return app

