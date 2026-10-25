@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher (py) was not found. Install Python 3.11+ or run on the PC where the app's Python is installed.
  pause
  exit /b 2
)
py run_full_tests.py
set RC=%ERRORLEVEL%
echo.
echo Report files are saved in this folder: FULL_TEST_REPORT.txt and FULL_TEST_REPORT.json
pause
exit /b %RC%
