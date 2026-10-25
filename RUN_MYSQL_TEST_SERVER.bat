@echo off
setlocal
cd /d "%~dp0"
py run_mysql_application.py --profile server
if errorlevel 1 pause
