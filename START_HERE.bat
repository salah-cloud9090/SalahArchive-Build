@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Salah Archive v16.13
if not exist logs mkdir logs
echo ================================================
echo Salah Archive - v16.13
echo ================================================
echo.
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ERROR: Python was not found on this computer.
  echo Install Python 3.10 or newer, then run START_HERE.bat again.
  pause
  exit /b 2
)
%PY% --version
if errorlevel 1 goto failed
%PY% -c "import requests,docx,openpyxl,pypdf,PIL,fitz,pytesseract,pdfplumber" >nul 2>nul
if errorlevel 1 (
  echo Some required Python packages are missing.
  if exist "requirements.txt" (
    echo Checking bundled offline packages...
    if exist "offline_packages\*.whl" (
      %PY% -m pip install --no-index --find-links="%CD%\offline_packages" -r requirements.txt
      if errorlevel 1 goto packages_missing
    ) else goto packages_missing
  )
)
echo.
echo Starting the archive application...
%PY% main.py
if errorlevel 1 goto failed
goto end
:packages_missing
echo Required packages are missing and could not be installed offline.
echo Run install_dependencies.bat only if Internet access is available.
goto failed
:failed
echo.
echo Startup failed. Run DIAGNOSTICS.bat and share diagnostics_report.txt.
pause
exit /b 1
:end
endlocal
