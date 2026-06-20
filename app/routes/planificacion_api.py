from flask import Blueprint, request, jsonify, session, current_app, render_template
from app import db
import app.models.base as models
from app.services.auth_service import login_required
import os
from werkzeug.utils import secure_filename
from datetime import datetime

planificacion_api_bp = Blueprint('planificacion_api', __name__, url_prefix='/docente/api/planificacion')

@planificacion_api_bp.route('/temas/', methods=['GET'])
@login_required
def get_temas():
    asignatura_id = request.args.get('asignatura_id')
    periodo_id = request.args.get('periodo_id')
    seccion = request.args.get('seccion')
    
    if not all([asignatura_id, periodo_id, seccion]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    temas_db = db.session.query(models.TemaClase).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion
    ).order_by(models.TemaClase.fecha_creacion).all()
    
    temas_data = []
    for tema in temas_db:
        materiales = db.session.query(models.MaterialApoyo).filter_by(tema_id=tema.id).all()
        tareas = db.session.query(models.TareaDocente).filter_by(tema_id=tema.id).all()
        
        m_data = [{
            'id': m.id,
            'titulo': m.titulo,
            'enlace': m.enlace,
            'archivo': f"/media/{m.archivo}" if m.archivo else None
        } for m in materiales]
        
        t_data = [{
            'id': t.id,
            'titulo': t.titulo,
            'instrucciones': t.instrucciones,
            'fecha_entrega': t.fecha_entrega.isoformat() if t.fecha_entrega else None
        } for t in tareas]
        
        temas_data.append({
            'id': tema.id,
            'titulo': tema.titulo,
            'descripcion': tema.descripcion,
            'fecha_programada': tema.fecha_programada.strftime('%Y-%m-%d') if tema.fecha_programada else None,
            'materiales': m_data,
            'tareas': t_data
        })
        
    return jsonify({'temas': temas_data})

@planificacion_api_bp.route('/tema/crear/', methods=['POST'])
@login_required
def crear_tema():
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion = data.get('seccion')
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fecha_programada = data.get('fecha_programada')
    docente_id = session.get('usuario_id')
    
    if not all([asignatura_id, periodo_id, seccion, titulo]):
        return jsonify({'error': 'Campos requeridos incompletos'}), 400
        
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado. Contacte al administrador.'}), 403
        
    fp = datetime.strptime(fecha_programada, '%Y-%m-%d') if fecha_programada else None
        
    tema = models.TemaClase(
        asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion,
        titulo=titulo, descripcion=descripcion, fecha_programada=fp, creado_por_id=docente_id,
        fecha_creacion=datetime.now()
    )
    db.session.add(tema)
    db.session.commit()
    
    return jsonify({'ok': True})

@planificacion_api_bp.route('/tema/eliminar/', methods=['POST'])
@login_required
def eliminar_tema():
    tema_id = request.json.get('tema_id')
    tema = db.session.query(models.TemaClase).get(tema_id)
    if tema:
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado. Contacte al administrador.'}), 403
            
        # Delete related materials and tasks first to avoid FK constraints issues
        db.session.query(models.MaterialApoyo).filter_by(tema_id=tema.id).delete()
        db.session.query(models.TareaDocente).filter_by(tema_id=tema.id).delete()
        db.session.delete(tema)
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'error': 'Tema no encontrado'}), 404

@planificacion_api_bp.route('/material/subir/', methods=['POST'])
@login_required
def subir_material():
    tema_id = request.form.get('tema_id')
    titulo = request.form.get('titulo')
    enlace = request.form.get('enlace')
    archivo = request.files.get('archivo')
    docente_id = session.get('usuario_id')
    
    tema = db.session.query(models.TemaClase).get(tema_id)
    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404
        
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado.'}), 403
        
    file_path = None
    if archivo:
        filename = secure_filename(archivo.filename)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'materiales')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = f"materiales/{filename}"
        archivo.save(os.path.join(upload_folder, filename))
        
    mat = models.MaterialApoyo(
        tema_id=tema_id, titulo=titulo, enlace=enlace, archivo=file_path,
        fecha_subida=datetime.now()
    )
    db.session.add(mat)
    db.session.commit()
    return jsonify({'ok': True})

@planificacion_api_bp.route('/material/eliminar/', methods=['POST'])
@login_required
def eliminar_material():
    material_id = request.json.get('material_id')
    mat = db.session.query(models.MaterialApoyo).get(material_id)
    if mat:
        tema = db.session.query(models.TemaClase).get(mat.tema_id)
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado.'}), 403
            
        db.session.delete(mat)
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'error': 'No encontrado'}), 404

@planificacion_api_bp.route('/tarea/crear/', methods=['POST'])
@login_required
def crear_tarea():
    data = request.json
    tema_id = data.get('tema_id')
    titulo = data.get('titulo')
    instrucciones = data.get('instrucciones')
    fecha_entrega = data.get('fecha_entrega')
    docente_id = session.get('usuario_id')
    
    tema = db.session.query(models.TemaClase).get(tema_id)
    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404
        
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado.'}), 403
        
    fe = datetime.strptime(fecha_entrega, '%Y-%m-%dT%H:%M') if fecha_entrega else None
        
    tarea = models.TareaDocente(
        tema_id=tema_id, titulo=titulo, instrucciones=instrucciones, fecha_entrega=fe,
        fecha_creacion=datetime.now()
    )
    db.session.add(tarea)
    db.session.commit()
    return jsonify({'ok': True})

@planificacion_api_bp.route('/tarea/eliminar/', methods=['POST'])
@login_required
def eliminar_tarea():
    tarea_id = request.json.get('tarea_id')
    tarea = db.session.query(models.TareaDocente).get(tarea_id)
    if tarea:
        tema = db.session.query(models.TemaClase).get(tarea.tema_id)
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado.'}), 403
            
        db.session.delete(tarea)
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'error': 'No encontrado'}), 404

@planificacion_api_bp.route('/tarea/editar/', methods=['POST'])
@login_required
def editar_tarea():
    data = request.json
    tarea_id = data.get('tarea_id')
    titulo = data.get('titulo')
    instrucciones = data.get('instrucciones')
    fecha_entrega = data.get('fecha_entrega')
    
    tarea = db.session.query(models.TareaDocente).get(tarea_id)
    if tarea:
        tema = db.session.query(models.TemaClase).get(tarea.tema_id)
        cierre = db.session.query(models.PeriodoCierre).filter_by(
            asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
        ).first()
        if cierre:
            return jsonify({'error': 'Período cerrado.'}), 403
            
        tarea.titulo = titulo
        tarea.instrucciones = instrucciones
        tarea.fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%dT%H:%M') if fecha_entrega else None
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'error': 'No encontrado'}), 404

@planificacion_api_bp.route('/perfil_docente/<int:docente_id>/plan_evaluacion/<int:asignatura_id>', methods=['GET'])
def obtener_plan_evaluacion(docente_id, asignatura_id):
    """
    Obtiene el plan de evaluación de un docente para una asignatura,
    renderizando el HTML listo para inyectarse en el Gestor de Expedientes.
    """
    try:
        seccion = request.args.get('seccion')

        # Consulta SQLAlchemy: filtramos y extraemos solo 3 campos (titulo, descripcion, fecha)
        query = db.session.query(
            models.TemaClase.titulo,
            models.TemaClase.descripcion,
            models.TemaClase.fecha_programada
        ).filter(
            models.TemaClase.creado_por_id == docente_id,
            models.TemaClase.asignatura_id == asignatura_id,
            models.TemaClase.activo == True
        )

        if seccion:
            query = query.filter(models.TemaClase.seccion == seccion)

        evaluaciones = query.order_by(models.TemaClase.fecha_programada.asc(), models.TemaClase.fecha_creacion.asc()).all()

        plan_datos = [
            {
                'titulo_tema': eval.titulo,
                'descripcion': eval.descripcion,
                'fecha_programada': eval.fecha_programada
            } for eval in evaluaciones
        ]

        response = render_template('docentes/fragmentos/_plan_evaluacion.html', plan_evaluacion=plan_datos)
        
        # Permitimos CORS para que el panel administrativo (Django) lo pueda cargar via AJAX
        resp = current_app.make_response(response)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    except Exception as e:
        print(f"Error al obtener el plan de evaluación: {e}")
        resp = current_app.make_response(jsonify({"error": "No se pudo cargar el plan de evaluación"}))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

@planificacion_api_bp.route('/api/plan_evaluacion/<int:docente_id>/<int:asignatura_id>', methods=['GET'])
def api_obtener_plan_evaluacion_json(docente_id, asignatura_id):
    """
    API JSON local para consultar los temas de un plan de evaluación.
    Retorna solo título, descripción y fecha programada.
    """
    import traceback
    try:
        seccion = request.args.get('seccion')

        query = db.session.query(
            models.TemaClase.titulo,
            models.TemaClase.descripcion,
            models.TemaClase.fecha_programada
        ).filter(
            models.TemaClase.creado_por_id == docente_id,
            models.TemaClase.asignatura_id == asignatura_id
        )

        if seccion:
            query = query.filter(models.TemaClase.seccion == seccion)

        evaluaciones = query.order_by(
            models.TemaClase.fecha_programada.asc(), 
            models.TemaClase.fecha_creacion.asc()
        ).all()

        temas = []
        for e in evaluaciones:
            temas.append({
                'titulo_tema': e.titulo,
                'descripcion': e.descripcion or '',
                'fecha_programada': e.fecha_programada.strftime('%Y-%m-%d') if e.fecha_programada else None
            })

        return jsonify({"temas": temas}), 200

    except Exception as e:
        db.session.rollback()
        print("===== ERROR EN API PLAN EVALUACION (FLASK) =====")
        traceback.print_exc()
        print("================================================")
        return jsonify({"error": f"Error interno en Flask: {str(e)}"}), 500

