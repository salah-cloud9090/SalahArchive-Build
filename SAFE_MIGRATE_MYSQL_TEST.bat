@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo SAFE MIGRATION HELPER - TEST DATABASE ONLY
echo The original database salah_archive is prohibited.
echo This does NOT switch main.py from SQLite to MySQL.
echo Do not use the legacy migrate_mysql_execute.bat launcher.
echo ============================================================
set /p CONFIRM=Type MIGRATE-TEST to continue: 
if not "%CONFIRM%"=="MIGRATE-TEST" goto end
python safe_migrate_sqlite_to_mysql.py --execute --confirm-target-database salah_archive_test
:end
pause
