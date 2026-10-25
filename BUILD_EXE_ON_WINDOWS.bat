@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build Salah Archive EXE v16.07
where py >nul 2>nul
if errorlevel 1 (echo Python launcher is missing. Install Python 3.11 x64 on this Windows PC, then retry.& pause & exit /b 2)
py -3.11 -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  if exist "offline_packages\pyinstaller*.whl" (py -3.11 -m pip install --no-index --find-links="offline_packages" pyinstaller)
  if errorlevel 1 (echo PyInstaller is not bundled. Prepare offline wheels or perform a one-time install before building.& pause & exit /b 3)
)
py -3.11 -m PyInstaller --noconfirm --clean --onedir --windowed --name SalahArchive --add-data "brand_logo.png;." --hidden-import fitz --hidden-import PIL --hidden-import pytesseract --hidden-import pdfplumber --hidden-import openpyxl --hidden-import docx --hidden-import mysql.connector main.py
if errorlevel 1 (echo EXE build failed.& pause & exit /b 4)
if not exist "dist\SalahArchive" (echo Build output folder is missing.& pause & exit /b 5)
rem Copy signed source files required by integrity_guard beside the EXE.
py -3.11 -c "import json,shutil,pathlib; base=pathlib.Path('.'); out=pathlib.Path('dist/SalahArchive'); m=json.loads((base/'integrity_manifest.json').read_text(encoding='utf-8')); [(out.joinpath(k).parent.mkdir(parents=True,exist_ok=True),shutil.copy2(base/k,out/k)) for k in m['files'] if (base/k).is_file()]; shutil.copy2(base/'integrity_manifest.json',out/'integrity_manifest.json'); shutil.copy2(base/'integrity_manifest.sig',out/'integrity_manifest.sig')"
if errorlevel 1 (echo Could not copy signed files to the EXE folder.& pause & exit /b 6)
echo EXE output: dist\SalahArchive\SalahArchive.exe
echo This build is a portable folder; keep the folder intact. MySQL Server and OCR language data must be installed/provided separately unless included in your organization's offline installer.
pause
