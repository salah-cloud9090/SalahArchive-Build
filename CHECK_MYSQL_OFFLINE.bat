@echo off
setlocal
cd /d "%~dp0"
set "MYSQL_EXE=%ProgramFiles%\MySQL\MySQL Server 8.4\bin\mysql.exe"
if exist "%MYSQL_EXE%" (
  echo Found MySQL command-line client at the standard MySQL Server 8.4 path.
  "%MYSQL_EXE%" --version
) else (
  where mysql >nul 2>nul
  if errorlevel 1 (
    echo mysql.exe is not in PATH. This is only a command-line PATH warning; the MySQL service can still run.
  ) else (
    mysql --version
  )
)
echo.
echo Checking MySQL Windows service...
sc query MySQL84
if errorlevel 1 sc query MySQL
echo.
echo This check does not run SQL or modify any database.
pause
