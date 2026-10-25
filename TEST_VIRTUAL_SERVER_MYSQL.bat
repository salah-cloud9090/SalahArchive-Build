@echo off
setlocal
cd /d "%~dp0"
echo Salah Archive v15.81 - VIRTUAL SERVER MySQL integration test
echo Target is restricted by the launcher to salah_archive_test.
py run_mysql_integration.py --profile server
if errorlevel 1 pause
