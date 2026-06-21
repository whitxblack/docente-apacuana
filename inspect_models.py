from app import create_app, db
import app.models.base as models

app = create_app()
with app.app_context():
    models.init_models()
    print("--- TemaClase ---")
    for col in models.TemaClase.__table__.columns:
        print(f"{col.name}: {col.type}")
        
    print("\n--- Evaluacion ---")
    for col in models.Evaluacion.__table__.columns:
        print(f"{col.name}: {col.type}")

    print("\n--- AsignacionDocente ---")
    for col in models.AsignacionDocente.__table__.columns:
        print(f"{col.name}: {col.type}")
