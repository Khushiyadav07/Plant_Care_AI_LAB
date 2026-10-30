@echo off
if not exist .venv\Scripts\activate.bat (
  echo Environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set FLASK_DEBUG=0
python run.py
pause
