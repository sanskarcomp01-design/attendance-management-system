@echo off
cd /d "%~dp0frontend"
call powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0frontend\scripts\setup-local-https.ps1"
if errorlevel 1 (
  echo HTTPS certificate setup failed. See the error above.
  pause
  exit /b 1
)
set AMS_LOCAL_HTTPS=1
call npm run dev -- --host 0.0.0.0 --strictPort
pause
