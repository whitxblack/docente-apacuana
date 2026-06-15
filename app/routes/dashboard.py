from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from app.models.base import Usuario, AsignacionDocente, Estudiante, Asignatura, PeriodoAcademico
from app.services.auth_service import login_required
from app import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/docente')

@dashboard_bp.route('/')
@login_required
def index():
    docente_id = session.get('usuario_id')
    
    # Obtener asignaciones activas del docente uniendo con Asignatura y PeriodoAcademico
    asignaciones_db = db.session.query(
        AsignacionDocente, Asignatura, PeriodoAcademico
    ).join(
        Asignatura, AsignacionDocente.asignatura_id == Asignatura.id
    ).join(
        PeriodoAcademico, AsignacionDocente.periodo_id == PeriodoAcademico.id
    ).filter(
        AsignacionDocente.docente_id == docente_id,
        AsignacionDocente.activa == True
    ).all()
    
    asignaciones = []
    for asig, asignatura, periodo in asignaciones_db:
        # Contar alumnos activos para el año y sección
        cantidad_alumnos = db.session.query(Estudiante).filter(
            Estudiante.ano_cursando == asig.ano_grado,
            Estudiante.seccion == asig.seccion,
            Estudiante.activo == True
        ).count()
        
        asignaciones.append({
            'ano_grado': asig.ano_grado,
            'seccion': asig.seccion,
            'aula': getattr(asig, 'aula', ''),
            'asignatura_nombre': asignatura.nombre,
            'asignatura_codigo': getattr(asignatura, 'codigo', ''),
            'periodo_nombre': periodo.nombre,
            'cantidad_alumnos': cantidad_alumnos
        })
        
    return render_template('docentes/dashboard_docente.html', asignaciones=asignaciones)

