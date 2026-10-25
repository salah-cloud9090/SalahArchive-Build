@echo off
cd /d "%~dp0"
echo WARNING: This copies all SQLite tables into the configured MySQL database.
echo It creates a SQLite backup and refuses to overwrite populated MySQL tables.
echo Keep local_archive_files unchanged. This does NOT switch main.py to MySQL yet.
set /p CONFIRM=Type MIGRATE to continue: 
if /I not "%CONFIRM%"=="MIGRATE" goto end
python migrate_sqlite_to_mysql.py --execute
:end
pause
