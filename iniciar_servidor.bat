@echo off
echo ====================================================
echo    Portal Docente APACUANA - Iniciando...
echo ====================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creando entorno virtual...
    python -m venv venv
    echo [INFO] Instalando dependencias...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    echo [INFO] Activando entorno virtual...
    call venv\Scripts\activate.bat
)

echo.
echo Iniciando servidor local (Flask)...
echo Sistema listo en: http://localhost:5000
echo Abriendo navegador automaticamente...
echo.
start http://localhost:5000
venv\Scripts\python.exe run.py
pause
