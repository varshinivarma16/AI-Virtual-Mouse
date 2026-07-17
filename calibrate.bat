@echo off
REM Double-click this file to calibrate your pinch, then the mouse starts.
REM Hold a thumb+index pinch still until the counter fills up.

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

echo Calibration: pinch thumb + index together and hold still...
"venv\Scripts\python.exe" main.py --calibrate

echo.
echo Done.
pause
