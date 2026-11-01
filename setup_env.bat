@echo off
REM Finance Dashboard - bootstrap a fresh virtual environment (Windows)
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Environment ready.
echo Double-click run_dashboard.bat to start the dashboard.
pause
