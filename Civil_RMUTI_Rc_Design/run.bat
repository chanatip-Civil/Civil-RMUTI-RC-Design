@echo off
REM Civil RMUTI Rc Design - double-click to run (Windows)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run: creating virtual environment and installing libraries...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Python was not found. Install Python 3.12+ from https://www.python.org and tick "Add Python to PATH".
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Library installation failed. Check your internet connection and try again.
        rmdir /s /q .venv
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
