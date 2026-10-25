@echo off
setlocal
cd /d "%~dp0"
py -m unittest discover -v
if errorlevel 1 goto failed
py -Werror::SyntaxWarning -m py_compile main_mysql_candidate_v15_79.py mysql_secure_config.py mysql_deployment_profiles.py
if errorlevel 1 goto failed
echo.
echo PASS: local tests and strict compile completed.
pause
exit /b 0
:failed
echo.
echo FAIL: inspect the test output above.
pause
exit /b 1
