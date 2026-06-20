from app import db
from sqlalchemy.ext.automap import automap_base

# Declaramos la base para mapear automáticamente las tablas existentes
Base = automap_base()

def reflect_database():
    # Reflejar las tablas desde la base de datos configurada
    with db.engine.connect() as conn:
        Base.prepare(autoload_with=db.engine)

# Clases mapeadas, se inicializarán después de reflect_database()
Usuario = None
Asignatura = None
PeriodoAcademico = None
AsignacionDocente = None
Evaluacion = None
NotaEvaluacion = None
Inscripcion = None
Estudiante = None
PerfilDocente = None
TemaClase = None
MaterialApoyo = None
TareaDocente = None
PeriodoCierre = None
RegistroAsistencia = None
AsistenciaGeneral = None

def init_models():
    global Usuario, Asignatura, PeriodoAcademico, AsignacionDocente
    global Evaluacion, NotaEvaluacion, Inscripcion, Estudiante
    global PerfilDocente, TemaClase, MaterialApoyo, TareaDocente, PeriodoCierre
    global RegistroAsistencia, AsistenciaGeneral
    
    reflect_database()
    
    # Mapeo a las tablas generadas por Django
    Usuario = Base.classes.get('usuarios_usuario')
    Asignatura = Base.classes.get('inscripciones_asignatura')
    PeriodoAcademico = Base.classes.get('inscripciones_periodoacademico')
    AsignacionDocente = Base.classes.get('docentes_asignaciondocente')
    Evaluacion = Base.classes.get('docentes_evaluacion')
    NotaEvaluacion = Base.classes.get('docentes_notaevaluacion')
    Inscripcion = Base.classes.get('inscripciones_inscripcion')
    Estudiante = Base.classes.get('estudiantes_estudiante')
    PerfilDocente = Base.classes.get('docentes_perfildocente')
    TemaClase = Base.classes.get('docentes_temaclase')
    MaterialApoyo = Base.classes.get('docentes_materialapoyo')
    TareaDocente = Base.classes.get('docentes_tareadocente')
    PeriodoCierre = Base.classes.get('docentes_periodocierre')
    RegistroAsistencia = Base.classes.get('docentes_registroasistencia')
    AsistenciaGeneral = Base.classes.get('asistencias_registroasistencia')
