from flask import Blueprint, request, jsonify, session
from app import db
import app.models.base as models
from app.services.auth_service import login_required
# pyrefly: ignore [missing-import]
from sqlalchemy import func
import traceback

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
        models.AsignacionDocente.ano_grado, models.AsignacionDocente.seccion
    ).filter(
        models.AsignacionDocente.docente_id == docente_id,
        models.AsignacionDocente.periodo_id == periodo_id,
        models.AsignacionDocente.activa == True
    ).distinct().order_by(models.AsignacionDocente.ano_grado, models.AsignacionDocente.seccion).all()
    
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
        
    asignaciones = db.session.query(models.AsignacionDocente, models.Asignatura).join(
        models.Asignatura, models.AsignacionDocente.asignatura_id == models.Asignatura.id
    ).filter(
        models.AsignacionDocente.docente_id == docente_id,
        models.AsignacionDocente.periodo_id == periodo_id,
        models.AsignacionDocente.ano_grado == int(ano_grado),
        models.AsignacionDocente.seccion == seccion,
        models.AsignacionDocente.activa == True
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
        
    estudiantes_db = db.session.query(models.Estudiante).filter(
        models.Estudiante.ano_cursando == int(ano_grado),
        models.Estudiante.seccion == seccion,
        models.Estudiante.activo == True
    ).order_by(models.Estudiante.apellidos, models.Estudiante.nombres).all()
    
    # Lazy enrollment: create inscriptions for students not yet enrolled this period
    nuevas = []
    for e in estudiantes_db:
        insc = db.session.query(models.Inscripcion).filter_by(
            estudiante_id=e.id, periodo_id=periodo_id
        ).first()
        if not insc:
            nuevas.append(models.Inscripcion(
                estudiante_id=e.id, periodo_id=periodo_id,
                ano_grado=int(ano_grado), seccion=seccion
            ))
    if nuevas:
        try:
            db.session.bulk_save_objects(nuevas)
            db.session.commit()
        except Exception:
            db.session.rollback()  # Don't let a duplicate key poison the session
    
    cierre = db.session.query(models.PeriodoCierre).filter_by(
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
        
    evaluaciones_db = db.session.query(models.Evaluacion).filter(
        models.Evaluacion.asignatura_id == asignatura_id,
        models.Evaluacion.periodo_id == periodo_id,
        models.Evaluacion.seccion == seccion,
        models.Evaluacion.activa == True
    ).order_by(models.Evaluacion.fecha_creacion).all()
    
    notas_qs = db.session.query(models.NotaEvaluacion, models.Inscripcion).join(
        models.Inscripcion, models.NotaEvaluacion.inscripcion_id == models.Inscripcion.id
    ).join(
        models.Evaluacion, models.NotaEvaluacion.evaluacion_id == models.Evaluacion.id
    ).filter(
        models.Evaluacion.asignatura_id == asignatura_id,
        models.Evaluacion.periodo_id == periodo_id,
        models.Evaluacion.seccion == seccion
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
    try:
        data = request.json
        asignatura_id = data.get('asignatura_id')
        periodo_id = data.get('periodo_id')
        seccion = data.get('seccion')
        tema_id = data.get('tema_id')
        nombre = data.get('nombre')
        tipo = data.get('tipo', 'EXAMEN')
        # Handle case where ponderacion is explicitly null in JSON
        pond_val = data.get('ponderacion')
        ponderacion = float(pond_val) if pond_val is not None else 0.0
        docente_id = session.get('usuario_id')
        
        if not all([asignatura_id, periodo_id, nombre, tema_id]):
            return jsonify({'error': 'Campos requeridos incompletos'}), 400
            
        if not (0 < ponderacion <= 100):
            return jsonify({'error': 'La ponderación debe estar entre 1 y 100'}), 400
            
        evals = db.session.query(models.Evaluacion).filter_by(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, activa=True
        ).all()
        suma_actual = sum([float(e.ponderacion) for e in evals])
        
        if suma_actual + ponderacion > 100:
            return jsonify({'error': f'Excedería el 100%. Disponible: {100 - suma_actual:.1f}%'}), 400
            
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado. Contacte al administrador.'}), 403
            
        tema = db.session.query(models.TemaClase).get(tema_id)
        if not tema:
            return jsonify({'error': 'Tema (Planificación) no encontrado'}), 404

        from datetime import datetime
        ev = models.Evaluacion(
            asignatura_id=asignatura_id, 
            periodo_id=periodo_id, 
            seccion=seccion,
            tema_id=tema.id,
            titulo_tema=tema.titulo,
            descripcion=tema.descripcion or '',
            nombre=nombre, 
            tipo=tipo, 
            ponderacion=ponderacion,
            creado_por_id=docente_id,
            fecha_creacion=datetime.now(),
            fecha_registro=datetime.now(),
            activa=True
        )
        db.session.add(ev)
        db.session.commit()
        return jsonify({'ok': True})
        
    except Exception as e:
        db.session.rollback()
        print("\n🚨 ERROR EN CREAR EVALUACIÓN:")
        traceback.print_exc()
        error_detail = str(e).split('\n')[0].strip()
        return jsonify({'error': f'DB Error: {error_detail}', 'traceback': traceback.format_exc()}), 500

@api_bp.route('/notas/guardar/', methods=['POST'])
@login_required
def guardar_notas():
    try:
        from datetime import datetime
        data = request.json
        notas = data.get('notas', [])
        es_borrador = data.get('es_borrador', True)
        asignatura_id = data.get('asignatura_id')
        periodo_id = data.get('periodo_id')
        seccion = data.get('seccion')
        ano_grado = data.get('ano_grado', 1)
        docente_id = session.get('usuario_id')
        
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado. No se pueden guardar notas.'}), 403
            
        guardadas = 0
        ahora = datetime.now()  # timestamp único para todo el batch
        
        for item in notas:
            est_id = int(item['estudiante_id'])
            eval_id = int(item['evaluacion_id'])
            nota = float(item['nota'])
            asistencia = item.get('asistencia', True)
            observacion = item.get('observacion', '')
            
            insc = db.session.query(models.Inscripcion).filter_by(
                estudiante_id=est_id, periodo_id=periodo_id
            ).first()
            if not insc:
                insc = models.Inscripcion(
                    estudiante_id=est_id, periodo_id=periodo_id,
                    ano_grado=int(ano_grado), seccion=seccion
                )
                db.session.add(insc)
                try:
                    db.session.commit()  # flush para obtener insc.id
                except Exception:
                    db.session.rollback()
                    continue  # skip this note if inscription fails
                
            nota_obj = db.session.query(models.NotaEvaluacion).filter_by(
                inscripcion_id=insc.id, evaluacion_id=eval_id
            ).first()
            
            if nota_obj:
                # UPDATE: refresh all mutable fields + always update fecha_registro
                nota_obj.nota = nota
                nota_obj.asistencia = asistencia
                nota_obj.observacion = observacion
                nota_obj.es_borrador = es_borrador
                nota_obj.registrado_por_id = docente_id
                nota_obj.fecha_registro = ahora
            else:
                # INSERT: set fecha_registro explicitly to avoid NOT NULL violation
                nota_obj = models.NotaEvaluacion(
                    inscripcion_id=insc.id, evaluacion_id=eval_id,
                    nota=nota, asistencia=asistencia, observacion=observacion,
                    es_borrador=es_borrador, registrado_por_id=docente_id,
                    fecha_registro=ahora
                )
                db.session.add(nota_obj)
            guardadas += 1
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("\n🚨 ERROR EN GUARDAR NOTAS:")
        traceback.print_exc()
        error_detail = str(e).split('\n')[0].strip()
        return jsonify({'error': f'DB Error: {error_detail}', 'traceback': traceback.format_exc()}), 500
    
    # Recalculate averages for all students in this course/section/period
    promedios = {}
    try:
        evals = db.session.query(models.Evaluacion).filter_by(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, activa=True
        ).all()
        eval_pond = {e.id: float(e.ponderacion) for e in evals}
        evals_ids = list(eval_pond.keys())
        
        if evals_ids:
            inscripciones = db.session.query(models.Inscripcion).filter_by(
                periodo_id=periodo_id, seccion=seccion, ano_grado=int(ano_grado)
            ).all()
            for insc in inscripciones:
                notas_db = db.session.query(models.NotaEvaluacion).filter(
                    models.NotaEvaluacion.inscripcion_id == insc.id,
                    models.NotaEvaluacion.evaluacion_id.in_(evals_ids)
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
    except Exception as e_prom:
        # Promedios failed but notes were saved — still return ok
        pass
            
    return jsonify({'ok': True, 'guardadas': guardadas, 'promedios': promedios})


@api_bp.route('/periodo/cerrar/', methods=['POST'])
@login_required
def cerrar_periodo():
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    docente_id = session.get('usuario_id')
    
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion
    ).first()
    
    from datetime import datetime
    try:
        if cierre:
            cierre.cerrado = True
            cierre.cerrado_por_id = docente_id
            cierre.fecha_cierre = datetime.utcnow()
        else:
            cierre = models.PeriodoCierre(
                asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion,
                cerrado=True, cerrado_por_id=docente_id, fecha_cierre=datetime.utcnow()
            )
            db.session.add(cierre)
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al cerrar período: {str(e)}'}), 500
        
    return jsonify({'ok': True})
