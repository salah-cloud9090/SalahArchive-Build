@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo SAFE MYSQL MIGRATION - TEST DATABASE ONLY
echo Target must be a clean database named salah_archive_test.
echo The original database salah_archive is prohibited.
echo Do NOT run the legacy migrate_mysql_execute.bat.
echo Set SALAH_MYSQL_PASSWORD in Windows environment first.
echo ============================================================
set /p SQLITE_PATH=Full path to docuware_archive.db (blank = this folder): 
if "%SQLITE_PATH%"=="" set "SQLITE_PATH=%~dp0docuware_archive.db"
set /p FILES_PATH=Full path to local_archive_files folder (blank = this folder): 
if "%FILES_PATH%"=="" set "FILES_PATH=%~dp0local_archive_files"
echo.
echo Source database: "%SQLITE_PATH%"
echo Files directory: "%FILES_PATH%"
echo Target database: salah_archive_test
set /p CONFIRM=Type MIGRATE-TEST to continue: 
if /I not "%CONFIRM%"=="MIGRATE-TEST" goto end
python safe_migrate_to_candidate.py --sqlite "%SQLITE_PATH%" --files "%FILES_PATH%" --config-dir "%~dp0" --execute --confirm-target-database salah_archive_test
:end
pause
