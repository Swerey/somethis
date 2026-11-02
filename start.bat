@echo off
REM ============================================================
REM  Hupu-style community platform - one-click start (M6)
REM  1) Recognition service serve.py   -> port 8000 (SERVE_PORT)
REM  2) Platform uvicorn main:app      -> port 8080 (--port)
REM  Ports can be changed by editing SERVE_PORT / PLATFORM_PORT
REM  below, keep them in sync with backend/config.py
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

set SERVE_PORT=8000
set PLATFORM_PORT=8080

echo [1/2] Starting recognition service on :8000 ...
start "Recognition-8000" cmd /k "cd /d C:\Users\swerey.SWEREY\PycharmProjects\PythonProject2\training && set SERVE_PORT=8000 && python serve.py"

echo [2/2] Starting platform on :8080 ...
start "Platform-8080" cmd /k "cd /d %~dp0backend && set PLATFORM_PORT=8080 && python -m uvicorn main:app --host 0.0.0.0 --port 8080"

echo.
echo Done. Platform: http://127.0.0.1:8080  Recognition: http://127.0.0.1:8000
echo Use stop.bat to stop both services.
pause
