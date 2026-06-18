from flask import Blueprint, render_template, session, request, jsonify
from app.models.base import AsignacionDocente, PeriodoAcademico
from app.services.auth_service import login_required
from app import db

calificaciones_bp = Blueprint('calificaciones', __name__, url_prefix='/docente/calificaciones')

@calificaciones_bp.route('/')
@login_required
def index():
    docente_id = session.get('usuario_id')
    
    # Obtener períodos donde el docente tiene asignaciones activas
    periodos_ids = db.session.query(AsignacionDocente.periodo_id).filter(
        AsignacionDocente.docente_id == docente_id,
        AsignacionDocente.activa == True
    ).distinct().all()
    
    periodos_ids = [p[0] for p in periodos_ids]
    
    if periodos_ids:
        periodos = db.session.query(PeriodoAcademico).filter(
            PeriodoAcademico.id.in_(periodos_ids)
        ).order_by(PeriodoAcademico.nombre.desc()).all()
    else:
        # Si no hay asignaciones, mostrar todos los periodos?
        periodos = db.session.query(PeriodoAcademico).order_by(PeriodoAcademico.nombre.desc()).all()
        
    return render_template('docentes/calificaciones_docente.html', periodos=periodos)
