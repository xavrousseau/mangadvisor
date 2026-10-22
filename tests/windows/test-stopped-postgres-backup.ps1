# Safe recovery rehearsal: NO Docker daemon, PostgreSQL data, or personal files.
# Exercise the real library-backup.ps1 function bodies with a synthetic Docker.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$fixture=Join-Path $env:RUNNER_TEMP ("ma_pg_recovery_"+[guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path $fixture | Out-Null
$script:envFile=Join-Path $fixture ".env"
$script:backups=Join-Path $fixture "backups"
$script:containerName="mangadvisor_postgres"
$script:pgDb="mangadvisor"
$script:pgUser="manga"
$script:NonInteractive=$false
$script:allow=$false
$script:running=$false
$script:containerExists=$true
$script:started=0
$script:commands=New-Object "System.Collections.Generic.List[string]"
$original=@'
POSTGRES_DB=mangadvisor
POSTGRES_USER=manga
POSTGRES_PASSWORD=RANDOM_NEW_SECRET
MEILI_MASTER_KEY=RANDOM_NEW_MEILI
API_PORT=8000
'@
[IO.File]::WriteAllText($script:envFile,$original,[Text.Encoding]::UTF8)

$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot "..\..\cmd\library-backup.ps1"),[Text.Encoding]::UTF8)
$tokens=$null
$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw "Script de sauvegarde invalide : $($errors -join '; ')" }
$defs=@($ast.FindAll({
  param($node)
  $node -is [Management.Automation.Language.FunctionDefinitionAst]
},$false))
if ($defs.Count -lt 10) { throw "Fonctions de sauvegarde manquantes." }
foreach ($def in $defs) {
  Invoke-Expression $def.Extent.Text
}

function docker {
  $argv=@($args)
  $script:commands.Add(($argv -join " "))
  $global:LASTEXITCODE=0
  if ($argv[0] -eq "container" -and $argv[1] -eq "ls") {
    if ($script:containerExists) { "mangadvisor_postgres" }
    "mangadvisor_meilisearch"
    return
  }
  if ($argv[0] -eq "volume" -and $argv[1] -eq "ls") { return }
  if ($argv[0] -eq "container" -and $argv[1] -eq "inspect") {
    $format=[string]$argv[3]
    $name=[string]$argv[4]
    if (-not $script:containerExists -and $name -eq "mangadvisor_postgres") {
      $global:LASTEXITCODE=1
      return
    }
    if ($format -match "Config.Env") {
      if ($name -eq "mangadvisor_postgres") {
        "POSTGRES_DB=mangadvisor"
        "POSTGRES_USER=manga"
        "POSTGRES_PASSWORD=ORIGINAL_SECRET_FROM_CONTAINER"
      } elseif ($name -eq "mangadvisor_meilisearch") {
        "MEILI_MASTER_KEY=ORIGINAL_MEILI_SECRET"
      }
      return
    }
    if ($format -match "Config.Labels") {
      if ($format -match "compose.service") {
        if ($name -eq "mangadvisor_postgres") { "postgres" } else { "meilisearch" }
      } else { "mangadvisor" }
      return
    }
    if ($format -match "State.Running") {
      if ($script:running) { "true" } else { "false" }
      return
    }
    "mock-id"
    return
  }
  if ($argv[0] -eq "start" -and $argv[1] -eq "mangadvisor_postgres") {
    $script:started++
    $script:running=$true
    "mangadvisor_postgres"
    return
  }
  if ($argv[0] -eq "exec" -and $argv[2] -eq "pg_isready") { return }
  if ($argv[0] -eq "exec" -and $argv[2] -eq "psql") { "manga"; return }
  if ($argv[0] -eq "exec" -and $argv[2] -eq "sh") { "1"; return }
  if ($argv[0] -eq "volume") {
    $global:LASTEXITCODE=1
    return
  }
  throw "Unexpected mock Docker command: $($argv -join ' ')"
}
function Confirm-Repair([string]$Question) { return $script:allow }

try {
  # 1. Owner refusal: no starting PostgreSQL, no secret rewrite.
  $denied=$false
  try { Prepare-Existing-Postgres } catch { $denied=$true }
  if (-not $denied) { throw "A refused secret repair must abort." }
  if ($script:started -ne 0) { throw "PostgreSQL started without approval." }
  if (([IO.File]::ReadAllText($script:envFile)) -cne $original) {
    throw "Refused recovery changed the original environment."
  }

  # 2. Explicit repair: original secrets are restored, old .env preserved,
  # and ONLY the existing stopped container is started.
  $script:allow=$true
  Prepare-Existing-Postgres
  $restored=[IO.File]::ReadAllText($script:envFile)
  if ($restored -notmatch 'POSTGRES_PASSWORD=ORIGINAL_SECRET_FROM_CONTAINER') {
    throw "Existing PostgreSQL credentials were not restored."
  }
  if ($restored -notmatch 'MEILI_MASTER_KEY=ORIGINAL_MEILI_SECRET') {
    throw "Existing Meilisearch credentials were not restored."
  }
  if ($restored -notmatch 'API_PORT=8000') {
    throw "Unrelated application configuration was changed."
  }
  $saved=@(Get-ChildItem -LiteralPath (Join-Path $script:backups "configuration") -File -Filter ".env_before_recovery_*")
  if ($saved.Count -ne 1 -or
      [IO.File]::ReadAllText($saved[0].FullName) -cne $original) {
    throw "Original .env was not preserved."
  }
  if ($script:started -ne 1 -or -not $script:running) {
    throw "Existing stopped PostgreSQL container not restarted."
  }
  if (@($script:commands | Where-Object { $_ -match '^(compose|rm|create|volume rm)(\\s|$)' }).Count -gt 0) {
    throw "An unsafe Compose/container/volume action was issued."
  }

  # 3. Repeating preflight must not change either secrets or containers.
  $script:allow=$false
  Prepare-Existing-Postgres
  if ($script:started -ne 1) { throw "Healthy PostgreSQL was restarted unexpectedly." }

  # 4. Missing existing PostgreSQL cannot be replaced with a new database.
  $script:containerExists=$false
  $blocked=$false
  try { Prepare-Existing-Postgres } catch { $blocked=$true }
  if (-not $blocked) { throw "A missing PostgreSQL container must block a backup." }
  if (@($script:commands | Where-Object { $_ -match '^(compose|rm|create|volume rm)(\\s|$)' }).Count -gt 0) {
    throw "A missing container triggered a dangerous replacement."
  }
  Write-Host "OK: stopped-container recovery, owner refusal, secret preservation, no recreation, missing-container blockade."
} finally {
  Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
}
