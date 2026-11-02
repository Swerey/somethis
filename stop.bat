@echo off
REM ============================================================
REM  Hupu-style community platform - one-click stop (M6)
REM  Kills processes LISTENING on port 8000 (recognition)
REM  and port 8080 (platform). Other processes are untouched.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo Stopping recognition service on :8000 ...
for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
  echo   killing PID %%A
  taskkill /F /PID %%A
)

echo Stopping platform on :8080 ...
for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":8080 " ^| findstr "LISTENING"') do (
  echo   killing PID %%A
  taskkill /F /PID %%A
)

echo.
echo All services stopped.
pause
