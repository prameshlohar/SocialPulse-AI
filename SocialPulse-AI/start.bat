@echo off
echo ========================================
echo   SocialPulse AI - Backend Server
echo ========================================
echo.

REM Find Python
set PYTHON_PATH=C:\Users\pc\AppData\Local\Python\bin\python.exe
if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=python
)

REM Create .env from example if missing
if not exist "%~dp0backend\.env" (
    echo [INFO] No .env found - running in Demo Mode
    echo [INFO] Copy backend\.env.example to backend\.env and add IBM credentials to enable AI
    echo.
)

echo [INFO] Starting Flask API server on http://localhost:5000
echo [INFO] Open frontend\index.html in your browser
echo.

cd /d "%~dp0backend"
set PYTHONUTF8=1
"%PYTHON_PATH%" app.py

pause
