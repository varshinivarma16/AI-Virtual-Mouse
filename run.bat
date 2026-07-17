@echo off
REM Double-click this file to start the AI Virtual Mouse.
REM It uses the bundled Python 3.11 virtual environment (no typing needed).

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo [ERROR] venv not found. Run setup first:
    echo     py -3.11 -m venv venv
    echo     venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Starting AI Virtual Mouse... press 'q' in the camera window to quit.
"venv\Scripts\python.exe" main.py

echo.
echo Virtual mouse stopped.
pause
