@echo off
cd /d "%~dp0"
python -m unittest discover -v
if errorlevel 1 goto :fail
python mysql_schema_index_audit.py
if errorlevel 1 goto :fail
python verify_python_compile.py
if errorlevel 1 goto :fail
echo.
echo PASS: local checks completed. This does NOT mean live MySQL is validated.
pause
exit /b 0
:fail
echo.
echo FAILED: inspect the test output above.
pause
exit /b 1
