param([ValidateSet('local','server')][string]$Profile = 'local', [switch]$NoGui)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$argsList = @((Join-Path $PSScriptRoot 'run_mysql_application.py'), '--profile', $Profile)
if ($NoGui) { $argsList += '--no-gui' }
& py @argsList
exit $LASTEXITCODE
