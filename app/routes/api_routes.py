from flask import Blueprint, request, jsonify, session
from app import db
from app.models.base import AsignacionDocente, Asignatura, Estudiante, Inscripcion, Evaluacion, NotaEvaluacion, PeriodoCierre, PeriodoAcademico
from app.services.auth_service import login_required
from sqlalchemy import func

api_bp = Blueprint('api', __name__, url_prefix='/docente/api')

MAPA_GRADOS = {1: '1er Año', 2: '2do Año', 3: '3er Año', 4: '4to Año', 5: '5to Año'}

@api_bp.route('/combinaciones/', methods=['GET'])
@login_required
def combinaciones():
    periodo_id = request.args.get('periodo_id')
    docente_id = session.get('usuario_id')
    
    if not periodo_id:
        return jsonify({'error': 'Periodo requerido'}), 400
        
    asignaciones = db.session.query(
        AsignacionDocente.ano_grado, AsignacionDocente.seccion
    ).filter(
        AsignacionDocente.docente_id == docente_id,
        AsignacionDocente.periodo_id == periodo_id,
        AsignacionDocente.activa == True
    ).distinct().order_by(AsignacionDocente.ano_grado, AsignacionDocente.seccion).all()
    
    data = []
    for a in asignaciones:
        data.append({
            'ano_grado': a.ano_grado,
            'seccion': a.seccion,
            'valor': f"{a.ano_grado}-{a.seccion}",
            'label': f"{MAPA_GRADOS.get(a.ano_grado, str(a.ano_grado))} - Sección {a.seccion}"
        })
        
    return jsonify({'combinaciones': data})

@api_bp.route('/materias-combo/', methods=['GET'])
@login_required
def materias_combo():
    periodo_id = request.args.get('periodo_id')
    ano_grado = request.args.get('ano_grado')
    seccion = request.args.get('seccion')
    docente_id = session.get('usuario_id')
    
    if not all([periodo_id, ano_grado, seccion]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    asignaciones = db.session.query(AsignacionDocente, Asignatura).join(
        Asignatura, AsignacionDocente.asignatura_id == Asignatura.id
    ).filter(
        AsignacionDocente.docente_id == docente_id,
        AsignacionDocente.periodo_id == periodo_id,
        AsignacionDocente.ano_grado == int(ano_grado),
        AsignacionDocente.seccion == seccion,
        AsignacionDocente.activa == True
    ).all()
    
    data = []
    seen = set()
    for asig, asignatura in asignaciones:
        if asignatura.id not in seen:
            seen.add(asignatura.id)
            data.append({'id': asignatura.id, 'nombre': asignatura.nombre})
            
    return jsonify({'materias': data})

@api_bp.route('/estudiantes/', methods=['GET'])
@login_required
def estudiantes():
    periodo_id = request.args.get('periodo_id')
    ano_grado = request.args.get('ano_grado')
    seccion = request.args.get('seccion')
    asignatura_id = request.args.get('asignatura_id')
    
    if not all([periodo_id, ano_grado, seccion, asignatura_id]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    estudiantes_db = db.session.query(Estudiante).filter(
        Estudiante.ano_cursando == int(ano_grado),
        Estudiante.seccion == seccion,
        Estudiante.activo == True
    ).order_by(Estudiante.apellidos, Estudiante.nombres).all()
    
    # Lazy enrollment (asegurar inscripciones)
    for e in estudiantes_db:
        insc = db.session.query(Inscripcion).filter_by(
            estudiante_id=e.id, periodo_id=periodo_id
        ).first()
        if not insc:
            nueva_insc = Inscripcion(
                estudiante_id=e.id, periodo_id=periodo_id,
                ano_grado=int(ano_grado), seccion=seccion
            )
            db.session.add(nueva_insc)
    db.session.commit()
    
    cierre = db.session.query(PeriodoCierre).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion
    ).first()
    
    data = []
    for e in estudiantes_db:
        data.append({
            'estudiante_id': e.id,
            'cedula': e.cedula_identidad,
            'nombre': f"{e.apellidos}, {e.nombres}",
            'telefono_representante': getattr(e, 'telefono_representante', '') or ''
        })
        
    return jsonify({
        'estudiantes': data,
        'cerrado': cierre.cerrado if cierre else False
    })

@api_bp.route('/evaluaciones/', methods=['GET'])
@login_required
def evaluaciones():
    asignatura_id = request.args.get('asignatura_id')
    periodo_id = request.args.get('periodo_id')
    seccion = request.args.get('seccion')
    
    if not all([asignatura_id, periodo_id, seccion]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    evaluaciones_db = db.session.query(Evaluacion).filter(
        Evaluacion.asignatura_id == asignatura_id,
        Evaluacion.periodo_id == periodo_id,
        Evaluacion.seccion == seccion,
        Evaluacion.activa == True
    ).order_by(Evaluacion.fecha_creacion).all()
    
    notas_qs = db.session.query(NotaEvaluacion, Inscripcion).join(
        Inscripcion, NotaEvaluacion.inscripcion_id == Inscripcion.id
    ).join(
        Evaluacion, NotaEvaluacion.evaluacion_id == Evaluacion.id
    ).filter(
        Evaluacion.asignatura_id == asignatura_id,
        Evaluacion.periodo_id == periodo_id,
        Evaluacion.seccion == seccion
    ).all()
    
    notas_map = {}
    for nota, insc in notas_qs:
        notas_map[f"{insc.estudiante_id}_{nota.evaluacion_id}"] = {
            'nota': nota.nota,
            'es_borrador': nota.es_borrador,
            'asistencia': nota.asistencia,
            'observacion': nota.observacion
        }
        
    suma = sum([e.ponderacion for e in evaluaciones_db])
    
    evals_data = [{
        'id': ev.id,
        'nombre': ev.nombre,
        'tipo': ev.tipo,
        'ponderacion': float(ev.ponderacion)
    } for ev in evaluaciones_db]
    
    return jsonify({
        'evaluaciones': evals_data,
        'notas': notas_map,
        'suma_ponderacion': float(suma)
    })

@api_bp.route('/evaluacion/crear/', methods=['POST'])
@login_required
def crear_evaluacion():
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    nombre = data.get('nombre')
    tipo = data.get('tipo', 'EXAMEN')
    ponderacion = float(data.get('ponderacion', 0))
    docente_id = session.get('usuario_id')
    
    if not all([asignatura_id, periodo_id, nombre]):
        return jsonify({'error': 'Campos requeridos incompletos'}), 400
        
    if not (0 < ponderacion <= 100):
        return jsonify({'error': 'La ponderación debe estar entre 1 y 100'}), 400
        
    evals = db.session.query(Evaluacion).filter_by(
        asignatura_id=int(asignatura_id), periodo_id=int(periodo_id), seccion=seccion, activa=True
    ).all()
    suma_actual = sum([e.ponderacion for e in evals])
    
    if suma_actual + ponderacion > 100:
        return jsonify({'error': f'Excedería el 100%. Disponible: {100 - suma_actual:.1f}%'}), 400
        
    cierre = db.session.query(PeriodoCierre).filter_by(
        asignatura_id=int(asignatura_id), periodo_id=int(periodo_id), seccion=seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado. Contacte al administrador.'}), 403
        
    try:
        from datetime import datetime
        ev = Evaluacion(
            asignatura_id=int(asignatura_id),
            periodo_id=int(periodo_id),
            seccion=seccion,
            nombre=nombre,
            tipo=tipo,
            ponderacion=ponderacion,
            creado_por_id=docente_id,
            fecha_creacion=datetime.now(),
            activa=True
        )
        db.session.add(ev)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar la evaluación en la base de datos: {str(e)}'}), 500
        
    return jsonify({'ok': True})

@api_bp.route('/notas/guardar/', methods=['POST'])
@login_required
def guardar_notas():
    data = request.json
    notas = data.get('notas', [])
    es_borrador = data.get('es_borrador', True)
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    ano_grado = data.get('ano_grado', 1)
    docente_id = session.get('usuario_id')
    
    cierre = db.session.query(PeriodoCierre).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado. No se pueden guardar notas.'}), 403
        
    guardadas = 0
    for item in notas:
        est_id = int(item['estudiante_id'])
        eval_id = int(item['evaluacion_id'])
        nota = float(item['nota'])
        asistencia = item.get('asistencia', True)
        observacion = item.get('observacion', '')
        
        insc = db.session.query(Inscripcion).filter_by(
            estudiante_id=est_id, periodo_id=periodo_id
        ).first()
        if not insc:
            insc = Inscripcion(estudiante_id=est_id, periodo_id=periodo_id, ano_grado=int(ano_grado), seccion=seccion)
            db.session.add(insc)
            db.session.commit()
            
        nota_obj = db.session.query(NotaEvaluacion).filter_by(
            inscripcion_id=insc.id, evaluacion_id=eval_id
        ).first()
        
        if nota_obj:
            nota_obj.nota = nota
            nota_obj.asistencia = asistencia
            nota_obj.observacion = observacion
            nota_obj.es_borrador = es_borrador
            nota_obj.registrado_por_id = docente_id
        else:
            nota_obj = NotaEvaluacion(
                inscripcion_id=insc.id, evaluacion_id=eval_id,
                nota=nota, asistencia=asistencia, observacion=observacion,
                es_borrador=es_borrador, registrado_por_id=docente_id
            )
            db.session.add(nota_obj)
        guardadas += 1
        
    db.session.commit()
    
    # Recalculate averages for all students in this course/section/period
    promedios = {}
    evals = db.session.query(Evaluacion).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, activa=True
    ).all()
    eval_pond = {e.id: float(e.ponderacion) for e in evals}
    evals_ids = list(eval_pond.keys())
    
    if evals_ids:
        inscripciones = db.session.query(Inscripcion).filter_by(
            periodo_id=periodo_id, seccion=seccion, ano_grado=int(ano_grado)
        ).all()
        for insc in inscripciones:
            notas_db = db.session.query(NotaEvaluacion).filter(
                NotaEvaluacion.inscripcion_id == insc.id,
                NotaEvaluacion.evaluacion_id.in_(evals_ids)
            ).all()
            
            suma_notas = 0.0
            suma_pond = 0.0
            hay_notas = False
            for n in notas_db:
                pond = eval_pond.get(n.evaluacion_id, 0.0)
                if n.nota is not None:
                    suma_notas += float(n.nota) * (pond / 100.0)
                    suma_pond += pond
                    hay_notas = True
            
            if hay_notas and suma_pond > 0:
                promedio = (suma_notas / (suma_pond / 100.0))
                promedios[insc.estudiante_id] = round(promedio, 2)
            else:
                promedios[insc.estudiante_id] = None
                
    return jsonify({'ok': True, 'guardadas': guardadas, 'promedios': promedios})

@api_bp.route('/periodo/cerrar/', methods=['POST'])
@login_required
def cerrar_periodo():
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    docente_id = session.get('usuario_id')
    
    cierre = db.session.query(PeriodoCierre).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion
    ).first()
    
    from datetime import datetime
    if cierre:
        cierre.cerrado = True
        cierre.cerrado_por_id = docente_id
        cierre.fecha_cierre = datetime.utcnow()
    else:
        cierre = PeriodoCierre(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion,
            cerrado=True, cerrado_por_id=docente_id, fecha_cierre=datetime.utcnow()
        )
        db.session.add(cierre)
        
    db.session.commit()
    return jsonify({'ok': True})
