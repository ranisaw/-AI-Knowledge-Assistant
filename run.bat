@echo off
echo =======================================================
echo Starting AI Knowledge Assistant (FastAPI + Web UI)
echo =======================================================
echo Access the web interface at: http://127.0.0.1:8000
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
pause
