@echo off
cd /d "%~dp0"
set "ST=.wins.financedashboard\Scripts\streamlit.exe"
if not exist "%ST%" set "ST=.venv\Scripts\streamlit.exe"
if not exist "%ST%" set "ST=streamlit.exe"

netstat -ano | findstr "LISTENING" | findstr ":8501 " >nul
if %errorlevel%==0 goto OPEN

start "Finance Dashboard" "%ST%" run app.py --server.port 8501 --server.runOnSave true --server.headless false
timeout /t 10 /nobreak >nul

:OPEN
start "" "http://localhost:8501"
echo Dashboard is serving at http://localhost:8501 in a separate console window.
timeout /t 3 /nobreak >nul
