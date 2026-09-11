@echo off
echo ============================================
echo   AI Finance System - Starting...
echo ============================================

echo.
echo [1/2] Starting Backend (Flask)...
start cmd /k "cd backend && venv\Scripts\activate && python app.py"

timeout /t 3

echo.
echo [2/2] Starting Frontend (HTTP Server)...
start cmd /k "cd frontend && python -m http.server 3000"

timeout /t 2

echo.
echo ============================================
echo   System Started!
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:3000
echo   Login:    http://localhost:3000/pages/login.html
echo ============================================

start http://localhost:3000/pages/login.html