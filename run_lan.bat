@echo off
REM SIET Helpdesk - Windows LAN Server Launcher
REM Automatically binds to 0.0.0.0 and displays your active local network IP address.

cd /d "%~dp0"

set PORT=%1
if "%PORT%"=="" set PORT=8000

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe manage.py runserver_lan %PORT%
) else if exist "win_venv\Scripts\python.exe" (
    win_venv\Scripts\python.exe manage.py runserver_lan %PORT%
) else (
    python manage.py runserver_lan %PORT%
)

pause
