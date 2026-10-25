@echo off
setlocal
cd /d "%~dp0"
py configure_mysql_profiles.py
if errorlevel 1 pause
