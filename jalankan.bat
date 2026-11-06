@echo off
rem Menjalankan Lamarin di komputer ini. Buka http://127.0.0.1:8000 setelah server siap.
cd /d "%~dp0"
python -m pip install -r requirements.txt --quiet
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
