import json
import urllib.request
from datetime import date

data = {
    "asignatura_id": 1,
    "periodo_id": 1,
    "seccion": "A",
    "fecha": "2026-06-18",
    "registros": [
        {"estudiante_id": 1, "estado": "PRESENTE", "observacion": "", "hora_llegada": "08:00"}
    ]
}

req = urllib.request.Request(
    'http://127.0.0.1:5000/docente/api/asistencia/registrar/',
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as res:
        print(res.read())
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
