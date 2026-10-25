@echo off
cd /d "%~dp0"
python migrate_sqlite_to_mysql.py
pause
