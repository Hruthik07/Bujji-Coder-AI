@echo off
REM Start script for Web UI (Windows)

echo Starting AI Coding Assistant Web UI...

REM Start backend
echo Starting backend server...
cd backend
start "Backend Server" python app.py
cd ..

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start frontend
echo Starting frontend...
cd frontend
start "Frontend Server" npm start
cd ..

echo.
echo Web UI started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close the windows to stop the servers.
pause
