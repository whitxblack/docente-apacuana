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
            'archivo': m.archivo if (m.archivo and m.archivo.startswith('http')) else (f"/media/{m.archivo}" if m.archivo else None)
        } for m in materiales]
        
        t_data = [{
            'id': t.id,
            'titulo': t.titulo,
            'instrucciones': t.instrucciones,
            'fecha_entrega': t.fecha_entrega.isoformat() if t.fecha_entrega else None
        } for t in tareas]
        
        evaluaciones = db.session.query(models.Evaluacion).filter_by(tema_id=tema.id).all()
        e_data = [{
            'id': e.id,
            'nombre': e.nombre,
            'ponderacion': float(e.ponderacion) if e.ponderacion else 0
        } for e in evaluaciones]
        
        temas_data.append({
            'id': tema.id,
            'titulo': tema.titulo,
            'descripcion': tema.descripcion,
            'fecha_programada': tema.fecha_programada.strftime('%Y-%m-%d') if tema.fecha_programada else None,
            'materiales': m_data,
            'tareas': t_data,
            'evaluaciones': e_data
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

@planificacion_api_bp.route('/tema/editar/', methods=['POST'])
@login_required
def editar_tema():
    data = request.json
    tema_id = data.get('tema_id')
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fecha_programada = data.get('fecha_programada')
    
    tema = db.session.query(models.TemaClase).get(tema_id)
    if not tema:
        return jsonify({'error': 'Tema no encontrado'}), 404
        
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'error': 'Período cerrado. Contacte al administrador.'}), 403
        
    fp = datetime.strptime(fecha_programada, '%Y-%m-%d') if fecha_programada else None
    
    tema.titulo = titulo
    tema.descripcion = descripcion
    tema.fecha_programada = fp
    db.session.commit()
    
    return jsonify({'ok': True})

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@planificacion_api_bp.route('/material/subir/', methods=['POST'])
@login_required
def subir_material():
    if 'archivo' in request.files and request.files['archivo'].filename != '' and not allowed_file(request.files['archivo'].filename):
        return jsonify({'success': False, 'message': 'Formato no permitido. Consulte los tipos de archivo válidos.'}), 400

    tema_id = request.form.get('tema_id')
    titulo = request.form.get('titulo')
    enlace = request.form.get('enlace')
    archivo = request.files.get('archivo')
    docente_id = session.get('usuario_id')
    
    tema = db.session.query(models.TemaClase).get(tema_id)
    if not tema:
        return jsonify({'success': False, 'message': 'Tema no encontrado'}), 404
        
    cierre = db.session.query(models.PeriodoCierre).filter_by(
        asignatura_id=tema.asignatura_id, periodo_id=tema.periodo_id, seccion=tema.seccion, cerrado=True
    ).first()
    if cierre:
        return jsonify({'success': False, 'message': 'Período cerrado.'}), 403
        
    file_path = None
    if archivo and archivo.filename != '':
        # Check size (Max 20MB)
        archivo.seek(0, os.SEEK_END)
        file_length = archivo.tell()
        archivo.seek(0)
        
        if file_length == 0:
            return jsonify({'success': False, 'message': 'El archivo no puede estar vacío.'}), 400
        if file_length > 20 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'El archivo excede el límite máximo permitido de 20 MB.'}), 400
            
        try:
            filename = secure_filename(archivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            safe_name = f"{timestamp}_{filename}"

            import cloudinary
            import cloudinary.uploader
            
            cloud_url = os.environ.get('CLOUDINARY_URL', '').replace('"', '').replace("'", "").strip()
            if 'CLOUDINARY_URL=' in cloud_url:
                cloud_url = cloud_url.split('CLOUDINARY_URL=', 1)[1].strip()
            
            if not cloud_url:
                return jsonify({'success': False, 'message': 'Fallo: No se detectó la variable CLOUDINARY_URL en el sistema.'}), 500
            
            os.environ['CLOUDINARY_URL'] = cloud_url
            
            if "cloudinary://" in cloud_url:
                cred_string = cloud_url.replace("cloudinary://", "")
                auth_part, cloud_name = cred_string.split("@")
                api_key, api_secret = auth_part.split(":")
                
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    secure=True
                )
            else:
                cloudinary.config(secure=True)
            
            res = cloudinary.uploader.upload(
                archivo,
                resource_type="raw",
                public_id=f"materiales/{safe_name}",
                use_filename=True
            )
            file_path = res.get('secure_url')
        except Exception as e:
            return jsonify({'success': False, 'message': f'Fallo al subir a Cloudinary: {str(e)}'}), 500
            
    try:
        mat = models.MaterialApoyo(
            tema_id=tema_id, titulo=titulo, enlace=enlace, archivo=file_path,
            fecha_subida=datetime.now()
        )
        db.session.add(mat)
        db.session.commit()
        return jsonify({'success': True, 'ok': True, 'message': 'Archivo guardado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Fallo interno al registrar: {str(e)}'}), 500

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
        return jsonify({'ok': True})
    return jsonify({'error': 'No encontrado'}), 404

@planificacion_api_bp.route('/clonar/', methods=['POST'])
@login_required
def clonar_planificacion():
    data = request.json
    asignatura_id = data.get('asignatura_id')
    periodo_id = data.get('periodo_id')
    seccion_origen = data.get('seccion')
    confirmacion = data.get('confirmacion')
    docente_id = session.get('usuario_id')
    
    if not all([asignatura_id, periodo_id, seccion_origen]):
        return jsonify({'error': 'Parámetros incompletos'}), 400
        
    try:
        # Obtener secciones destino (misma asignatura y periodo, distinta seccion)
        asignaciones = db.session.query(models.AsignacionDocente).filter_by(
            docente_id=docente_id,
            asignatura_id=asignatura_id,
            periodo_id=periodo_id,
            activa=True
        ).filter(models.AsignacionDocente.seccion != seccion_origen).all()
        
        target_sections = list(set([a.seccion for a in asignaciones]))
        
        if not target_sections:
            return jsonify({'error': 'No tienes otras secciones asignadas para esta materia en este período.'}), 404
            
        # Verificar conflictos
        conflict_sections = []
        clean_sections = []
        
        for sec in target_sections:
            count = db.session.query(models.TemaClase).filter_by(
                asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=sec
            ).count()
            if count > 0:
                conflict_sections.append(sec)
            else:
                clean_sections.append(sec)
                
        # Si hay conflictos y no hay confirmacion previa, devolver estado conflict
        if conflict_sections and not confirmacion:
            return jsonify({
                'status': 'conflict',
                'conflictos': conflict_sections
            })
            
        sections_to_clone = clean_sections
        
        # Procesar según la confirmación
        if confirmacion == 'overwrite':
            # Borrar las existentes de las secciones con conflicto
            for sec in conflict_sections:
                temas_viejos = db.session.query(models.TemaClase).filter_by(
                    asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=sec
                ).all()
                for tv in temas_viejos:
                    # Borrar evaluaciones asociadas
                    db.session.query(models.Evaluacion).filter_by(tema_id=tv.id).delete()
                    # (Opcional) Borrar MaterialApoyo y TareaDocente si existen
                    db.session.query(models.MaterialApoyo).filter_by(tema_id=tv.id).delete()
                    db.session.query(models.TareaDocente).filter_by(tema_id=tv.id).delete()
                    db.session.delete(tv)
            sections_to_clone.extend(conflict_sections)
            
        # Obtener la planificación origen
        temas_origen = db.session.query(models.TemaClase).filter_by(
            asignatura_id=asignatura_id, periodo_id=periodo_id, seccion=seccion_origen
        ).all()
        
        if not temas_origen:
            return jsonify({'error': 'La sección de origen no tiene planificación cargada.'}), 404
            
        # Inserción (Duplicación)
        for sec_dest in sections_to_clone:
            for tema in temas_origen:
                # Clonar Tema
                nuevo_tema = models.TemaClase(
                    asignatura_id=asignatura_id,
                    periodo_id=periodo_id,
                    seccion=sec_dest,
                    titulo=tema.titulo,
                    descripcion=tema.descripcion,
                    fecha_programada=tema.fecha_programada,
                    creado_por_id=docente_id,
                    fecha_creacion=datetime.now()
                )
                db.session.add(nuevo_tema)
                db.session.flush() # Para obtener nuevo_tema.id
                
                # Clonar Evaluaciones de este tema
                evaluaciones = db.session.query(models.Evaluacion).filter_by(tema_id=tema.id).all()
                for ev in evaluaciones:
                    nueva_ev = models.Evaluacion(
                        tema_id=nuevo_tema.id,
                        asignatura_id=asignatura_id,
                        periodo_id=periodo_id,
                        seccion=sec_dest,
                        nombre=ev.nombre,
                        tipo=ev.tipo if hasattr(ev, 'tipo') else None,
                        ponderacion=ev.ponderacion,
                        creado_por_id=docente_id,
                        activa=True,
                        fecha_creacion=datetime.now()
                    )
                    db.session.add(nueva_ev)
                    
        db.session.commit()
        return jsonify({'status': 'success', 'cloned_to': sections_to_clone})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al clonar planificación: {str(e)}'}), 500

@planificacion_api_bp.route('/perfil_docente/<int:docente_id>/plan_evaluacion/<int:asignatura_id>', methods=['GET'])
def obtener_plan_evaluacion(docente_id, asignatura_id):
    """
    Obtiene el plan de evaluación de un docente para una asignatura,
    renderizando el HTML listo para inyectarse en el Gestor de Expedientes.
    """
    try:
        seccion = request.args.get('seccion')

        # Consulta SQLAlchemy: filtramos y extraemos TemaClase y Evaluacion
        query = db.session.query(
            models.TemaClase.id.label('tema_id'),
            models.TemaClase.titulo,
            models.TemaClase.descripcion,
            models.TemaClase.fecha_programada,
            models.Evaluacion.id.label('evaluacion_id'),
            models.Evaluacion.nombre.label('evaluacion_nombre')
        ).outerjoin(
            models.Evaluacion, models.TemaClase.id == models.Evaluacion.tema_id
        ).filter(
            models.TemaClase.creado_por_id == docente_id,
            models.TemaClase.asignatura_id == asignatura_id,
            models.TemaClase.activo == True
        )

        if seccion:
            query = query.filter(models.TemaClase.seccion == seccion)

        resultados = query.order_by(models.TemaClase.fecha_programada.asc(), models.TemaClase.fecha_creacion.asc()).all()

        plan_dict = {}
        for row in resultados:
            t_id = row.tema_id
            if t_id not in plan_dict:
                plan_dict[t_id] = {
                    'titulo_tema': row.titulo,
                    'descripcion': row.descripcion,
                    'fecha_programada': row.fecha_programada,
                    'evaluaciones': []
                }
            if row.evaluacion_id:
                plan_dict[t_id]['evaluaciones'].append({
                    'id': row.evaluacion_id,
                    'nombre': row.evaluacion_nombre
                })
        
        plan_datos = list(plan_dict.values())

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
            models.TemaClase.id.label('tema_id'),
            models.TemaClase.titulo,
            models.TemaClase.descripcion,
            models.TemaClase.fecha_programada,
            models.Evaluacion.id.label('evaluacion_id'),
            models.Evaluacion.nombre.label('evaluacion_nombre')
        ).outerjoin(
            models.Evaluacion, models.TemaClase.id == models.Evaluacion.tema_id
        ).filter(
            models.TemaClase.creado_por_id == docente_id,
            models.TemaClase.asignatura_id == asignatura_id
        )

        if seccion:
            query = query.filter(models.TemaClase.seccion == seccion)

        resultados = query.order_by(
            models.TemaClase.fecha_programada.asc(), 
            models.TemaClase.fecha_creacion.asc()
        ).all()

        plan_dict = {}
        for row in resultados:
            t_id = row.tema_id
            if t_id not in plan_dict:
                plan_dict[t_id] = {
                    'titulo_tema': row.titulo,
                    'descripcion': row.descripcion or '',
                    'fecha_programada': row.fecha_programada.strftime('%Y-%m-%d') if row.fecha_programada else None,
                    'evaluaciones': []
                }
            if row.evaluacion_id:
                plan_dict[t_id]['evaluaciones'].append({
                    'id': row.evaluacion_id,
                    'nombre': row.evaluacion_nombre
                })
        
        temas = list(plan_dict.values())

        return jsonify({"temas": temas}), 200

    except Exception as e:
        db.session.rollback()
        print("===== ERROR EN API PLAN EVALUACION (FLASK) =====")
        traceback.print_exc()
        print("================================================")
        return jsonify({"error": f"Error interno en Flask: {str(e)}"}), 500

