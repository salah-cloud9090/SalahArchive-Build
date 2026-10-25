@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo WARNING: This resets the LOCAL TEST database and local test files.
echo A backup will be created first. Do not run this on production data.
echo Close the archive application before continuing.
echo.
choice /C YN /M "Continue with backup and reset"
if errorlevel 2 goto cancelled

set "STAMP=%RANDOM%_%RANDOM%"
set "BACKUP=backups\reset_%STAMP%"
if not exist "%BACKUP%" mkdir "%BACKUP%"
if errorlevel 1 goto backup_failed

if exist "docuware_archive.db" copy /Y "docuware_archive.db" "%BACKUP%\docuware_archive.db"
if errorlevel 1 goto backup_failed

if exist "local_archive_files" xcopy "local_archive_files" "%BACKUP%\local_archive_files\" /E /I /H /K /Y
if errorlevel 1 goto backup_failed

if exist "processed_outputs" xcopy "processed_outputs" "%BACKUP%\processed_outputs\" /E /I /H /K /Y
if errorlevel 1 goto backup_failed

echo.
echo Backup created at: %BACKUP%
echo Check that this backup exists before resetting.
echo.
choice /C YN /M "Delete the current test database and working files now"
if errorlevel 2 goto kept_backup

if exist "docuware_archive.db" del /Q "docuware_archive.db"
if exist "local_archive_files" rmdir /S /Q "local_archive_files"
if exist "processed_outputs" rmdir /S /Q "processed_outputs"
mkdir "local_archive_files"
mkdir "processed_outputs"

echo.
echo Reset finished. Backup is preserved in %BACKUP%
echo Run run_local_archive.bat to create a fresh test database.
goto end

:backup_failed
echo.
echo ERROR: Backup failed. Nothing was intentionally deleted.
echo Check folder permissions and free disk space.
goto end

:kept_backup
echo.
echo Reset cancelled. Existing database and files were kept.
goto end

:cancelled
echo.
echo Cancelled. Nothing changed.

:end
echo.
pause
