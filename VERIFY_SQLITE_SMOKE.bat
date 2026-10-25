@echo off
setlocal
cd /d "%~dp0"
python smoke_test_sqlite_isolated.py
if errorlevel 1 (
  echo.
  echo Smoke test FAILED. Review the error above.
  pause
  exit /b 1
)
echo.
echo Smoke test passed. This did not test live MySQL.
pause
