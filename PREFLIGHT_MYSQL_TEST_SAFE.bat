@echo off
setlocal
cd /d "%~dp0"
echo Read-only source/file preflight. No MySQL connection or writes.
set /p SQLITE_PATH=Full path to docuware_archive.db (blank = this folder): 
if "%SQLITE_PATH%"=="" set "SQLITE_PATH=%~dp0docuware_archive.db"
set /p FILES_PATH=Full path to local_archive_files folder (blank = this folder): 
if "%FILES_PATH%"=="" set "FILES_PATH=%~dp0local_archive_files"
python safe_migrate_to_candidate.py --sqlite "%SQLITE_PATH%" --files "%FILES_PATH%" --config-dir "%~dp0"
pause
