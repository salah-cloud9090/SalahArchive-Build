@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Install Salah Archive Offline OCR
set "SETUP=%~dp0tesseract-ocr-w64-setup-5.5.3.20260724.exe"
if not exist "%SETUP%" (echo Missing Tesseract installer. Run PREPARE_OFFLINE_OCR.bat on an internet-connected PC first.& pause & exit /b 2)
for %%L in (ara eng osd) do if not exist "%~dp0%%L.traineddata" (echo Missing %%L.traineddata. Offline OCR pack is incomplete.& pause & exit /b 3)
echo This will launch the Tesseract installer. Follow its prompts.
echo Install to the default location: C:\Program Files\Tesseract-OCR
start /wait "" "%SETUP%"
if not exist "C:\Program Files\Tesseract-OCR\tessdata" (echo Could not find the default Tesseract tessdata folder. If you chose another path, copy ara/eng/osd.traineddata into its tessdata folder manually.& pause & exit /b 4)
copy /Y "%~dp0ara.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\ara.traineddata" >nul
copy /Y "%~dp0eng.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" >nul
copy /Y "%~dp0osd.traineddata" "C:\Program Files\Tesseract-OCR\tessdata\osd.traineddata" >nul
if errorlevel 1 (echo ERROR copying language data.& pause & exit /b 5)
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" ("C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs & echo Confirm ara, eng, and osd appear above.) else (echo Tesseract executable not found at default location. Check installer path.)
pause
