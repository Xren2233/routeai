@echo off
start "Backend"  cmd /k "cd /d %~dp0backend && python app.py"
start "Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 8080"
timeout /t 2 /nobreak >nul
start http://localhost:8080
