@echo off
setlocal
cd /d "%~dp0"
python -m unittest discover -v
if errorlevel 1 goto failed
python mysql_schema_index_audit.py
if errorlevel 1 goto failed
python mysql_candidate_gate.py
if errorlevel 1 goto failed
python verify_python_compile.py
if errorlevel 1 goto failed
echo.
echo Local static verification passed. This does NOT replace a live MySQL test.
pause
exit /b 0
:failed
echo.
echo Verification failed. Read the test output and reports above.
pause
exit /b 1
