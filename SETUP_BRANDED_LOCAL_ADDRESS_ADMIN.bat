@echo off
chcp 65001 >nul
setlocal
net session >nul 2>&1
if errorlevel 1 (
  echo Please follow the instructions shown in this window.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'; $line='127.0.0.1 civilid-archive.test'; $c=Get-Content -LiteralPath $p -Raw; if($c -notmatch '(?m)^\s*127\.0\.0\.1\s+civilid-archive\.test\s*$'){Add-Content -LiteralPath $p -Value $line -Encoding ascii}; ipconfig /flushdns | Out-Null"
if errorlevel 1 (
 echo Please follow the instructions shown in this window.
 pause
 exit /b 1
)
echo Please follow the instructions shown in this window.
echo Please follow the instructions shown in this window.
pause
