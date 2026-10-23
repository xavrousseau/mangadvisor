# Offline PowerShell 5.1 test. No Docker Desktop or real data involved.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$source=Join-Path $PSScriptRoot "..\..\cmd\control-center.ps1"
$tokens=$null
$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count -ne 0) { throw "Invalid PowerShell controller." }
$defs=@($ast.FindAll({
  param($node)
  $node -is [Management.Automation.Language.FunctionDefinitionAst]
},$false))
foreach ($name in @("Assert-Exit","Run","Remove-Legacy-Ui")) {
  $match=@($defs | Where-Object { $_.Name -ceq $name })
  if ($match.Count -ne 1) { throw "Missing function $name" }
  Invoke-Expression $match[0].Extent.Text
}
$script:present=$true
$script:labels='{"com.docker.compose.project":"mangadvisor","com.docker.compose.service":"ui"}'
$script:removed=0
function docker {
  $argv=@($args)
  $global:LASTEXITCODE=0
  if ($argv[0] -eq "container" -and $argv[1] -eq "ls") {
    if ($script:present) { "mangadvisor_ui" }
    return
  }
  if ($argv[0] -eq "container" -and $argv[1] -eq "inspect") {
    $script:labels
    return
  }
  if ($argv[0] -eq "rm" -and $argv[1] -eq "-f" -and $argv[2] -eq "mangadvisor_ui") {
    $script:removed++
    return
  }
  throw "Unexpected Docker invocation: $($argv -join ' ')"
}
$script:present=$false
Remove-Legacy-Ui
if ($script:removed -ne 0) { throw "Removed missing UI." }
$script:present=$true
foreach ($json in @(
  '{}',
  '{"com.docker.compose.project":"foreign","com.docker.compose.service":"ui"}',
  '{"com.docker.compose.project":"mangadvisor","com.docker.compose.service":"api"}',
  'not-json'
)) {
  $script:labels=$json
  $refused=$false
  try { Remove-Legacy-Ui } catch { $refused=$true }
  if (-not $refused -or $script:removed -ne 0) {
    throw "Unsafe removal with labels: $json"
  }
}
$script:labels='{"com.docker.compose.project":"mangadvisor","com.docker.compose.service":"ui"}'
Remove-Legacy-Ui
if ($script:removed -ne 1) { throw "Expected one verified owned UI removal." }
Write-Host "OK: foreign containers are protected; only the owned retired UI can be removed."
