import sys
import json
from app import create_app, db
from app.models.base import RegistroAsistencia

app = create_app()

with app.app_context():
    # Attempt to query RegistroAsistencia
    try:
        res = db.session.query(RegistroAsistencia).first()
        print("Query successful. First row:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
