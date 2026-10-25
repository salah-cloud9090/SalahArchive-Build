@echo off
setlocal
cd /d "%~dp0"
py run_mysql_integration.py --profile server
if errorlevel 1 pause
