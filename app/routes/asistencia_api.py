from flask import Blueprint, request, jsonify, session
from app import db
import app.models.base as models
from app.services.auth_service import login_required
from datetime import date, datetime
from sqlalchemy import func, case

asistencia_api_bp = Blueprint('asistencia_api', __name__, url_prefix='/docente/api/asistencia')

@asistencia_api_bp.route('/registrar/', methods=['POST'])
@login_required
def registrar():
    """Guarda la asistencia masiva de una lista de estudiantes para una fecha."""
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    fecha_str = data.get('fecha')
    registros = data.get('registros', [])
    docente_id = session.get('usuario_id')
    
    if not all([asignatura_id, periodo_id, seccion, fecha_str]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    guardados = 0
    
    for item in registros:
        est_id = int(item['estudiante_id'])
        estado = item.get('estado', 'PRESENTE')
        observacion = item.get('observacion', '')
        hora_llegada_str = item.get('hora_llegada')
        
        hora_llegada = None
        if hora_llegada_str:
            try:
                hora_llegada = datetime.strptime(hora_llegada_str, '%H:%M').time()
            except ValueError:
                pass
        
        # Buscar registro existente (upsert)
        existente = db.session.query(models.RegistroAsistencia).filter_by(
            estudiante_id=est_id,
            asignatura_id=asignatura_id,
            periodo_id=periodo_id,
            seccion=seccion,
            fecha=fecha
        ).first()
        
        if existente:
            existente.estado = estado
            existente.observacion = observacion
            existente.hora_llegada = hora_llegada
            existente.registrado_por_id = docente_id
            existente.hora_registro = datetime.now()
        else:
            reg = models.RegistroAsistencia(
                estudiante_id=est_id,
                asignatura_id=asignatura_id,
                periodo_id=periodo_id,
                seccion=seccion,
                fecha=fecha,
                estado=estado,
                observacion=observacion,
                hora_llegada=hora_llegada,
                metodo='MANUAL',
                registrado_por_id=docente_id,
                hora_registro=datetime.now()
            )
            db.session.add(reg)
        guardados += 1
        
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar asistencia: {str(e)}'}), 500
        
    return jsonify({'ok': True, 'guardados': guardados})

@asistencia_api_bp.route('/obtener/', methods=['GET'])
@login_required
def obtener():
    """Obtiene los registros de asistencia de una fecha específica."""
    asignatura_id = request.args.get('asignatura_id')
    periodo_id = request.args.get('periodo_id')
    seccion = request.args.get('seccion')
    fecha_str = request.args.get('fecha')
    
    if not all([asignatura_id, periodo_id, seccion, fecha_str]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    registros = db.session.query(models.RegistroAsistencia).filter_by(
        asignatura_id=asignatura_id,
        periodo_id=periodo_id,
        seccion=seccion,
        fecha=fecha
    ).all()
    
    data = {}
    for r in registros:
        data[str(r.estudiante_id)] = {
            'estado': r.estado,
            'observacion': r.observacion,
            'hora_llegada': r.hora_llegada.strftime('%H:%M') if r.hora_llegada else None,
            'metodo': r.metodo
        }
        
    return jsonify({'registros': data})

@asistencia_api_bp.route('/historial/', methods=['GET'])
@login_required
def historial():
    """Obtiene el historial de fechas en las que se ha pasado asistencia."""
    asignatura_id = request.args.get('asignatura_id')
    periodo_id = request.args.get('periodo_id')
    seccion = request.args.get('seccion')
    
    if not all([asignatura_id, periodo_id, seccion]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    fechas = db.session.query(
        models.RegistroAsistencia.fecha,
        func.count(models.RegistroAsistencia.id).label('total'),
        func.sum(
            case((models.RegistroAsistencia.estado == 'PRESENTE', 1), else_=0)
        ).label('presentes'),
        func.sum(
            case((models.RegistroAsistencia.estado == 'AUSENTE', 1), else_=0)
        ).label('ausentes'),
        func.sum(
            case((models.RegistroAsistencia.estado == 'RETARDO', 1), else_=0)
        ).label('retardos'),
        func.sum(
            case((models.RegistroAsistencia.estado == 'JUSTIFICADO', 1), else_=0)
        ).label('justificados')
    ).filter(
        models.RegistroAsistencia.asignatura_id == asignatura_id,
        models.RegistroAsistencia.periodo_id == periodo_id,
        models.RegistroAsistencia.seccion == seccion
    ).group_by(models.RegistroAsistencia.fecha).order_by(models.RegistroAsistencia.fecha.desc()).all()
    
    data = [{
        'fecha': f.fecha.strftime('%Y-%m-%d'),
        'total': f.total,
        'presentes': int(f.presentes or 0),
        'ausentes': int(f.ausentes or 0),
        'retardos': int(f.retardos or 0),
        'justificados': int(f.justificados or 0)
    } for f in fechas]
    
    return jsonify({'historial': data})

@asistencia_api_bp.route('/estadisticas/', methods=['GET'])
@login_required
def estadisticas():
    """Estadísticas de asistencia por estudiante en un rango de período."""
    asignatura_id = request.args.get('asignatura_id')
    periodo_id = request.args.get('periodo_id')
    seccion = request.args.get('seccion')
    ano_grado = request.args.get('ano_grado')
    
    if not all([asignatura_id, periodo_id, seccion, ano_grado]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    # Obtener total de clases registradas
    total_clases = db.session.query(
        func.count(func.distinct(models.RegistroAsistencia.fecha))
    ).filter(
        models.RegistroAsistencia.asignatura_id == asignatura_id,
        models.RegistroAsistencia.periodo_id == periodo_id,
        models.RegistroAsistencia.seccion == seccion
    ).scalar() or 0
    
    # Obtener estudiantes de esa sección
    estudiantes = db.session.query(models.Estudiante).filter(
        models.Estudiante.ano_cursando == int(ano_grado),
        models.Estudiante.seccion == seccion,
        models.Estudiante.activo == True
    ).order_by(models.Estudiante.apellidos, models.Estudiante.nombres).all()
    
    stats = []
    for est in estudiantes:
        regs = db.session.query(
            models.RegistroAsistencia.estado,
            func.count(models.RegistroAsistencia.id)
        ).filter(
            models.RegistroAsistencia.estudiante_id == est.id,
            models.RegistroAsistencia.asignatura_id == asignatura_id,
            models.RegistroAsistencia.periodo_id == periodo_id,
            models.RegistroAsistencia.seccion == seccion
        ).group_by(models.RegistroAsistencia.estado).all()
        
        conteo = {r[0]: r[1] for r in regs}
        presentes = conteo.get('PRESENTE', 0) + conteo.get('JUSTIFICADO', 0)
        porcentaje = round((presentes / total_clases * 100), 1) if total_clases > 0 else 0
        
        stats.append({
            'estudiante_id': est.id,
            'nombre': f"{est.apellidos}, {est.nombres}",
            'cedula': est.cedula_identidad,
            'presentes': conteo.get('PRESENTE', 0),
            'ausentes': conteo.get('AUSENTE', 0),
            'retardos': conteo.get('RETARDO', 0),
            'justificados': conteo.get('JUSTIFICADO', 0),
            'porcentaje': porcentaje
        })
        
    return jsonify({
        'estadisticas': stats,
        'total_clases': total_clases
    })
