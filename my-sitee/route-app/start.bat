@echo off
echo Starting RouteAI...

start "Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && python app.py"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d %~dp0frontend && python -m http.server 8080"
timeout /t 2 /nobreak >nul

start http://localhost:8080
echo Done! Backend: http://localhost:5000 ^| Frontend: http://localhost:8080
