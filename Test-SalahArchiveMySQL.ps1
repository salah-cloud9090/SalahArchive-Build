param([ValidateSet('local','server')][string]$Profile = 'local')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& py (Join-Path $PSScriptRoot 'run_mysql_integration.py') --profile $Profile
exit $LASTEXITCODE
