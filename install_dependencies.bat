@echo off
setlocal EnableExtensions
cd /d "%~dp0"
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
echo This installer may need Internet access unless offline wheels are bundled.
%PY% -m pip install -r requirements.txt
if errorlevel 1 echo Dependency installation failed. Check Python and Internet access.
pause
endlocal
