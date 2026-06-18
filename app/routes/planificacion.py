from flask import Blueprint, render_template, session, request, jsonify
from app.models.base import AsignacionDocente, PeriodoAcademico
from app.services.auth_service import login_required
from app import db

planificacion_bp = Blueprint('planificacion', __name__, url_prefix='/docente/planificacion')

@planificacion_bp.route('/')
@login_required
def index():
    docente_id = session.get('usuario_id')
    
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
        periodos = db.session.query(PeriodoAcademico).order_by(PeriodoAcademico.nombre.desc()).all()
        
    return render_template('docentes/planificacion_docente.html', periodos=periodos)
