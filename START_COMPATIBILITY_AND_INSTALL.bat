@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Salah Archive - Adaptive Compatibility Setup
set "REPORT=%CD%\SalahArchive_Compatibility_Report.txt"
>"%REPORT%" echo Salah Archive Adaptive Compatibility Report
>>"%REPORT%" echo Date: %DATE% %TIME%
>>"%REPORT%" echo Computer: %COMPUTERNAME%
>>"%REPORT%" echo Windows:
ver >>"%REPORT%" 2>&1
>>"%REPORT%" echo Architecture:
echo PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%>>"%REPORT%"
>>"%REPORT%" echo Python launchers:
where py >>"%REPORT%" 2>&1
py -0p >>"%REPORT%" 2>&1
>>"%REPORT%" echo Python package import check:
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  >>"%REPORT%" echo Python not found.
  echo Python is missing. The application source mode needs Python.
  echo For a prebuilt EXE, use the signed portable EXE folder instead.
  start notepad "%REPORT%"
  pause
  exit /b 2
)
%PY% --version >>"%REPORT%" 2>&1
%PY% -c "import requests,docx,openpyxl,pypdf,PIL,fitz,pytesseract,pdfplumber,cryptography" >>"%REPORT%" 2>&1
if errorlevel 1 (
  echo Required Python libraries are missing.
  if exist "offline_packages\*.whl" (
    echo Trying local offline wheelhouse first...
    %PY% -m pip install --no-index --find-links="%CD%\offline_packages" -r requirements.txt
  ) else (
    echo No offline wheels found. The setup needs Internet access to fetch compatible packages.
    choice /C YN /M "Connect to the Internet and install required Python packages now"
    if errorlevel 2 goto missing
    %PY% -m pip install --upgrade pip
    if errorlevel 1 goto installfailed
    %PY% -m pip install -r requirements.txt
  )
  if errorlevel 1 goto installfailed
)
>>"%REPORT%" echo [Tesseract]
where tesseract >>"%REPORT%" 2>&1
tesseract --list-langs >>"%REPORT%" 2>&1
>>"%REPORT%" echo [MySQL]
sc query MySQL84 >>"%REPORT%" 2>&1
sc query MySQL80 >>"%REPORT%" 2>&1
mysql --version >>"%REPORT%" 2>&1
>>"%REPORT%" echo [LM Studio API]
powershell -NoProfile -ExecutionPolicy Bypass -Command "try {$r=Invoke-RestMethod 'http://127.0.0.1:1234/v1/models' -TimeoutSec 3; 'API reachable'; $r.data | ForEach-Object {$_.id}} catch {'API not reachable or no local server: '+$_.Exception.Message}" >>"%REPORT%" 2>&1
>>"%REPORT%" echo [Preview libraries]
%PY% -c "import fitz,PIL; print('PyMuPDF and Pillow imports OK')" >>"%REPORT%" 2>&1
>>"%REPORT%" echo [Offline installers]
dir /s /b offline_packages >>"%REPORT%" 2>&1
echo.
echo Compatibility scan complete. Report: %REPORT%
start notepad "%REPORT%"
echo.
echo If required Python packages were installed, you can now run START_HERE.bat.
echo Note: MySQL MSI, Windows Tesseract binaries/Arabic data, and the AI model are not bundled unless separately present in offline_packages or installed locally.
pause
exit /b 0
:missing
echo Setup cancelled; no packages were installed.
start notepad "%REPORT%"
pause
exit /b 3
:installfailed
>>"%REPORT%" echo Package installation failed. Check Internet, Python version, and pip errors above.
echo Installation failed. See the report and console errors.
start notepad "%REPORT%"
pause
exit /b 4
