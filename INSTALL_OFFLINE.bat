@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\SalahArchive\SalahArchive.exe" (
 echo The EXE has not been built yet. Run BUILD_EXE_ON_WINDOWS.bat first.
 pause
 exit /b 2
)
set "DEST=%LOCALAPPDATA%\SalahArchive"
if not exist "%DEST%" mkdir "%DEST%"
robocopy "dist\SalahArchive" "%DEST%" /E /COPY:DAT /R:1 /W:1 >nul
copy /Y "license_core.py" "%DEST%\license_core.py" >nul
copy /Y "integrity_guard.py" "%DEST%\integrity_guard.py" >nul
copy /Y "integrity_manifest.json" "%DEST%\integrity_manifest.json" >nul
copy /Y "integrity_manifest.sig" "%DEST%\integrity_manifest.sig" >nul
if errorlevel 8 (echo Copy failed.& pause & exit /b 3)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Salah Archive.lnk');$s.TargetPath='%DEST%\SalahArchive.exe';$s.WorkingDirectory='%DEST%';$s.Save()"
echo Installation files copied. First launch requires offline activation.
echo Note: this script installs an already-built EXE; it does not fetch anything from the Internet.
pause
