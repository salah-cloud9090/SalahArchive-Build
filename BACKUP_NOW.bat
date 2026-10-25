@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Archive Backup
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ERROR: Python was not found.
  pause
  exit /b 2
)
if not exist backup_restore.py (
  echo ERROR: backup_restore.py is missing from this folder.
  pause
  exit /b 3
)
%PY% backup_restore.py backup
if errorlevel 1 (
  echo ERROR: Backup failed. Do not delete or move archive files.
  pause
  exit /b 1
)
echo Backup completed. Check the backups folder.
pause
endlocal
