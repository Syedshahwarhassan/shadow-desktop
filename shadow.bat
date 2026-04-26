@echo off
:: This script allows you to run the Shadow Assistant (AntiGravity) from anywhere.
:: To use it globally, add this folder to your system PATH.

setlocal
:: Change directory to the script's location
cd /d "%~dp0"

:: Check if virtual environment exists, otherwise use system python
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py %*
) else (
    python main.py %*
)

endlocal
