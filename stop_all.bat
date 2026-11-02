@echo off
echo stopping all python processes ...
taskkill /F /IM python.exe /T >nul 2>&1
echo done.
