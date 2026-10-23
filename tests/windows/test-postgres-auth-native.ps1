# Windows PowerShell 5.1: exercise real native argument and stdin forwarding
# via a disposable docker.cmd shim. No Docker daemon, passwords or user files.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$folder=Join-Path $env:RUNNER_TEMP ("ma_pg_auth_"+[guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$dockerShim=Join-Path $folder "docker.cmd"
$oldPath=$env:PATH
$oldFail=$env:MA_AUTH_SHIM_FAIL
$body=@'
@echo off
if not "%~1"=="exec" exit /b 51
if not "%~2"=="-i" exit /b 52
if not "%~3"=="mangadvisor_postgres" exit /b 53
if not "%~4"=="sh" exit /b 54
if not "%~5"=="-c" exit /b 55
if not "%~6"=="PGPASSWORD=$POSTGRES_PASSWORD exec psql -h postgres -X -At -U $POSTGRES_USER -d $POSTGRES_DB" exit /b 56
set /p INPUT_SQL=
if not "%INPUT_SQL%"=="SELECT 1" exit /b 57
if "%MA_AUTH_SHIM_FAIL%"=="1" exit /b 58
echo 1
'@
try {
  [IO.File]::WriteAllText($dockerShim,$body,(New-Object Text.ASCIIEncoding))
  $env:PATH=$folder+";"+$oldPath
  $backup=Join-Path $PSScriptRoot "..\\..\\cmd\\library-backup.ps1"
  $tokens=$null
  $parseErrors=$null
  $ast=[Management.Automation.Language.Parser]::ParseFile($backup,[ref]$tokens,[ref]$parseErrors)
  if ($parseErrors.Count -ne 0) { throw "Invalid PowerShell backup script." }
  $definitions=@($ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst]
  },$false))
  $fn=@($definitions | Where-Object { $_.Name -ceq "Test-Api-Password" })
  if ($fn.Count -ne 1) { throw "Missing unique Test-Api-Password." }
  Invoke-Expression $fn[0].Extent.Text
  function Container-Exists([string]$name) { return $false }
  $script:containerName="mangadvisor_postgres"
  $resolved=(Get-Command docker -ErrorAction Stop).Source
  if (-not $resolved.StartsWith($folder,[StringComparison]::OrdinalIgnoreCase)) {
    throw "Native shim not selected."
  }
  $env:MA_AUTH_SHIM_FAIL="0"
  if (-not (Test-Api-Password)) { throw "Actual native TCP probe failed." }
  $env:MA_AUTH_SHIM_FAIL="1"
  if (Test-Api-Password) { throw "Failed PostgreSQL authentication was accepted." }
  Write-Host "OK: Windows PowerShell 5.1 preserved Docker shell argument and SQL stdin."
} finally {
  $env:PATH=$oldPath
  if ($null -eq $oldFail) { Remove-Item Env:\\MA_AUTH_SHIM_FAIL -ErrorAction SilentlyContinue }
  else { $env:MA_AUTH_SHIM_FAIL=$oldFail }
  Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue
}
