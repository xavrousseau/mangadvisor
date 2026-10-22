# Native Windows PowerShell 5.1 regression: call a real docker.cmd process.
# A mocked PowerShell function cannot reproduce quote-stripping on native args.
# No Docker daemon, secrets, volumes, or user files touched.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$dir=Join-Path $env:RUNNER_TEMP ("ma_docker_labels_"+[guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$shim=Join-Path $dir "docker.cmd"
$log=Join-Path $dir "args.txt"
$oldPath=$env:PATH
$oldLog=$env:MA_DOCKER_LABEL_ARGLOG
$body=@'
@echo off
if not "%~1"=="container" exit /b 51
if not "%~2"=="inspect" exit /b 52
if not "%~3"=="--format" exit /b 53
if not "%~4"=="{{json .Config.Labels}}" exit /b 64
echo %~4>> "%MA_DOCKER_LABEL_ARGLOG%"
if "%~5"=="mangadvisor_postgres" (
echo {"com.docker.compose.service":"postgres","com.docker.compose.project":"mangadvisor"}
exit /b 0
)
if "%~5"=="mangadvisor_meilisearch" (
echo {"com.docker.compose.service":"meilisearch","com.docker.compose.project":"mangadvisor"}
exit /b 0
)
exit /b 55
'@
try {
  [IO.File]::WriteAllText($shim,$body,(New-Object Text.ASCIIEncoding))
  [IO.File]::WriteAllText($log,"",(New-Object Text.ASCIIEncoding))
  $env:MA_DOCKER_LABEL_ARGLOG=$log
  $env:PATH=$dir+";"+$oldPath
  $backup=Join-Path $PSScriptRoot "..\..\cmd\library-backup.ps1"
  $tokens=$null
  $errors=$null
  $ast=[Management.Automation.Language.Parser]::ParseFile($backup,[ref]$tokens,[ref]$errors)
  if ($errors.Count -ne 0) { throw "Backup script does not parse in Windows PowerShell 5.1." }
  $wanted=@("Assert-Ok","Assert-Managed-Container")
  $defs=@($ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst]
  },$false))
  foreach ($name in $wanted) {
    $d=@($defs | Where-Object { $_.Name -eq $name })
    if ($d.Count -ne 1) { throw "Missing function $name" }
    Invoke-Expression $d[0].Extent.Text
  }
  $resolved=(Get-Command docker -ErrorAction Stop).Source
  if (-not $resolved.StartsWith($dir,[StringComparison]::OrdinalIgnoreCase)) {
    throw "Native docker.cmd fixture not selected: $resolved"
  }
  Assert-Managed-Container "mangadvisor_postgres" "postgres"
  Assert-Managed-Container "mangadvisor_meilisearch" "meilisearch"
  $argsRead=@(Get-Content -LiteralPath $log)
  if ($argsRead.Count -ne 2 -or
      $argsRead[0].Trim() -cne "{{json .Config.Labels}}" -or
      $argsRead[1].Trim() -cne "{{json .Config.Labels}}") {
    throw "PowerShell did not pass the Go-template JSON argument unchanged to native Docker."
  }
  Write-Host "OK: Windows PowerShell 5.1 passed the quote-safe JSON label template to native Docker for both services."
} finally {
  $env:PATH=$oldPath
  if ($null -eq $oldLog) { Remove-Item Env:\MA_DOCKER_LABEL_ARGLOG -ErrorAction SilentlyContinue }
  else { $env:MA_DOCKER_LABEL_ARGLOG=$oldLog }
  Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
}
