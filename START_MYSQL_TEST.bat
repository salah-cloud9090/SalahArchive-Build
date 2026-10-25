@echo off
setlocal
cd /d "%~dp0"
py run_mysql_application.py
if errorlevel 1 pause
