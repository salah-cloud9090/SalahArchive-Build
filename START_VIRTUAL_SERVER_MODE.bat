@echo off
setlocal
cd /d "%~dp0"
echo Salah Archive v15.81 - VIRTUAL SERVER MODE
 echo This uses only the TEST database: salah_archive_test
 echo MySQL host is 127.0.0.1 on this same PC.
echo LOCAL UI TEST MODE: activation bypass applies ONLY to this PC (127.0.0.1).
echo LAN clients remain activation-protected. TEST DATABASE ONLY.
set SALAH_ARCHIVE_LOCAL_UI_TEST=1
py run_mysql_application.py --profile server
if errorlevel 1 pause
