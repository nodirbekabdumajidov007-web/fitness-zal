@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual muhit yaratilmoqda...
  python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" manage.py migrate
".venv\Scripts\python.exe" manage.py setup_gym --demo
echo.
echo Sayt: http://localhost:8000   Admin: parol oxiriga .admin qo'shib kiring
start "" "http://localhost:8000"
".venv\Scripts\python.exe" -m uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --reload --reload-dir gym --reload-dir config
pause
