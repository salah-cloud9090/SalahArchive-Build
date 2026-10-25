@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Administrative Archive
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
%PY% main.py
if errorlevel 1 pause
endlocal
