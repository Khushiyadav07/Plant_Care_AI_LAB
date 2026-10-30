@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. Install Python 3.11 64-bit from https://www.python.org/downloads/ and enable Add Python to PATH.
  pause
  exit /b 1
)
py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 was not found. Install Python 3.11 64-bit, then run this file again.
  pause
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 goto fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto fail
pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Setup complete. Double-click start_windows.bat to run Plant Care AI.
pause
exit /b 0
:fail
echo.
echo Setup failed. Check the error above. Make sure Python 3.11 64-bit is installed.
pause
exit /b 1
