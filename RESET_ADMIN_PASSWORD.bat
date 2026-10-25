@echo off
setlocal
cd /d "%~dp0"
title Archive Admin Password Reset
echo.
echo Administrative Archive - Admin Password Reset
echo This changes only the admin password and keeps archive data.
echo Close the archive application and browser before continuing.
echo.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 reset_admin_password.py
  goto :finish
)
where python >nul 2>nul
if not errorlevel 1 (
  python reset_admin_password.py
  goto :finish
)
echo ERROR: Python 3 was not found on PATH.
echo Open the project folder in File Explorer and install Python 3, or run this on the PC where Python is installed.
:finish
echo.
pause
