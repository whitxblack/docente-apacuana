import json
from app import create_app

app = create_app()
client = app.test_client()

data = {
    "asignatura_id": 1,
    "periodo_id": 1,
    "seccion": "A",
    "fecha": "2026-06-18",
    "registros": [
        {"estudiante_id": 1, "estado": "PRESENTE", "observacion": "", "hora_llegada": "08:00"}
    ]
}

# we also need to simulate login for @login_required
with client.session_transaction() as sess:
    sess['usuario_id'] = 1
    sess['rol'] = 'docente'

res = client.post('/docente/api/asistencia/registrar/', 
                  data=json.dumps(data), 
                  content_type='application/json')
print("Status:", res.status_code)
print("Response:", res.get_data(as_text=True))
