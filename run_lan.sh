#!/usr/bin/env bash
# SIET Helpdesk - LAN Server Launcher
# Automatically binds to 0.0.0.0 and displays your active local network IP address.

cd "$(dirname "$0")"

PORT="${1:-8000}"

if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -f "./win_venv/Scripts/python.exe" ]; then
    PYTHON_CMD="./win_venv/Scripts/python.exe"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD manage.py runserver_lan "$PORT"
