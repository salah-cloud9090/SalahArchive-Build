@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Prepare Salah Archive Offline OCR Pack
set "TESS_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.5.3.20260724.exe"
set "DATA_URL=https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main"
echo.
echo Salah Archive - Offline OCR pack downloader
echo This step requires internet and only downloads files into this folder.
echo Afterward, copy the whole folder to offline PCs.
echo.
where powershell >nul 2>nul
if errorlevel 1 (echo ERROR: Windows PowerShell is required.& pause & exit /b 2)
echo Downloading Tesseract Windows installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%TESS_URL%' -OutFile 'tesseract-ocr-w64-setup-5.5.3.20260724.exe'"
if errorlevel 1 (echo ERROR: Installer download failed. Check internet and official download availability.& pause & exit /b 3)
for %%L in (ara eng osd) do (
  echo Downloading %%L language data...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%DATA_URL%/%%L.traineddata' -OutFile '%%L.traineddata'"
  if errorlevel 1 (echo ERROR: Could not download %%L.traineddata& pause & exit /b 4)
)
echo.
echo Verifying files exist and are non-empty...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=@('tesseract-ocr-w64-setup-5.5.3.20260724.exe','ara.traineddata','eng.traineddata','osd.traineddata'); $bad=@($f | Where-Object { !(Test-Path $_) -or (Get-Item $_).Length -lt 1000 }); if($bad.Count){$bad; exit 5}; Get-FileHash $f -Algorithm SHA256 | Format-Table -AutoSize"
if errorlevel 1 (echo ERROR: File verification failed.& pause & exit /b 5)
echo.
echo SUCCESS: Offline OCR files are now stored in:
echo %CD%
echo Keep this folder with the Salah Archive package for offline installation.
pause
