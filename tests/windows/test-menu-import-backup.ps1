# Exercises the menu-driven import sequence under Windows PowerShell 5.1.
# Does not start Docker, call the API, or write to a personal database.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "..\..\cmd\control-center.ps1") -Action Environment
$csv=Join-Path $root "private-data\mangatheque.csv"
[IO.File]::WriteAllText($csv,"serie;tomes_principaux`r`nCI test;1`r`n")
$script:events=New-Object "System.Collections.Generic.List[string]"
$script:allow=$true
function powershell.exe {
  $arguments=@($args)
  if ($arguments -contains "-PreviewOnly") {
    $script:events.Add("preview")
  } else {
    $script:events.Add("apply")
  }
  $global:LASTEXITCODE=0
}
function Confirm([string]$Question,[bool]$Default=$false) { return $script:allow }
function Backup { $script:events.Add("backup") }

try {
  Inventory
  if (($script:events -join ",") -cne "preview,backup,apply") {
    throw "Backup was not guaranteed between preview and database import: $($script:events -join ',')"
  }

  $script:events.Clear()
  $script:allow=$false
  Inventory
  if (($script:events -join ",") -cne "preview") {
    throw "A preview-only/cancelled import must not create a backup or write: $($script:events -join ',')"
  }

  $script:events.Clear()
  $script:allow=$true
  function Backup {
    $script:events.Add("backup")
    throw "Synthetic backup failure"
  }
  $failed=$false
  try { Inventory } catch {
    $failed=$_.Exception.Message -like "*Synthetic backup failure*"
  }
  if (-not $failed -or ($script:events -join ",") -cne "preview,backup") {
    throw "Backup failure did not prevent inventory import: $($script:events -join ',')"
  }
  Write-Host "OK: no physical inventory import without a verified backup."
} finally {
  Remove-Item -LiteralPath $csv -Force -ErrorAction SilentlyContinue
}
