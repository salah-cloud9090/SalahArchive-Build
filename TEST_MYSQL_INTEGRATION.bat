@echo off
setlocal
cd /d "%~dp0"
py run_mysql_integration.py --profile local
if errorlevel 1 pause
