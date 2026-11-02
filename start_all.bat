@echo off
cd /d "C:\Users\swerey.SWEREY\PycharmProjects\系统"
echo [1/2] starting danmu recognizer on :8000 ...
start "danmu-recognizer" "D:\rgzn\1\envs\torch_gpu\python.exe" -m uvicorn recognizer.serve:app --host 0.0.0.0 --port 8000
timeout /t 5 /nobreak >nul
echo [2/2] starting platform ...
call start.bat
