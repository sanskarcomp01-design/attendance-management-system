@echo off
start "Attendance Backend" cmd /k call "%~dp0start-backend.bat"
timeout /t 2 /nobreak >nul
start "Attendance HTTPS Website" cmd /k call "%~dp0start-frontend.bat"
