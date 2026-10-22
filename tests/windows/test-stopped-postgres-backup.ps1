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
$script:loginFixed=$false
$script:brokenLabels=$false
$script:wrongProject=$false
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
      # Simulate Docker's Go-template parser: embedded quoted map keys
      # are LOST by Windows PowerShell 5.1 native argument marshaling.
      if ($format -cne "{{json .Config.Labels}}") {
        throw "Go template parsing error: function com not defined"
      }
      if ($script:brokenLabels) { "{not valid json"; return }
      $service=if ($name -eq "mangadvisor_postgres") { "postgres" } else { "meilisearch" }
      $project=if ($script:wrongProject) { "other_project" } else { "mangadvisor" }
      # Return a realistic Docker JSON labels object in ONE native output line.
      '{"com.docker.compose.service":"' + $service +
        '","com.docker.compose.project":"' + $project + '"}'
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
  if ($argv[0] -eq "exec" -and $argv[1] -eq "-i") {
    $script:loginFixed=$true
    return
  }
  if ($argv[0] -eq "exec" -and $argv[2] -eq "sh") {
    if ($script:loginFixed) { "1" } else { $global:LASTEXITCODE=1 }
    return
  }
  if ($argv[0] -eq "volume") {
    $global:LASTEXITCODE=1
    return
  }
  throw "Unexpected mock Docker command: $($argv -join ' ')"
}
function Confirm-Repair([string]$Question) { return $script:allow }

try {
  # 0. Reproduce the exact Windows go-template failure safely:
  # the service and project labels must be parsed from a JSON map, never
  # from a Go 'index .Config.Labels "com...."' template.
  Assert-Managed-Container "mangadvisor_postgres" "postgres"
  Assert-Managed-Container "mangadvisor_meilisearch" "meilisearch"
  $dockerLabelCalls=@($script:commands | Where-Object { $_ -match 'inspect --format \{\{json \.Config\.Labels\}\}' })
  if ($dockerLabelCalls.Count -ne 2) {
    throw "The real label checks are not using the quote-safe Docker JSON template."
  }
  $script:brokenLabels=$true
  $rejected=$false
  try { Assert-Managed-Container "mangadvisor_postgres" "postgres" } catch { $rejected=$true }
  if (-not $rejected) { throw "Malformed Docker label JSON was accepted." }
  $script:brokenLabels=$false
  $script:wrongProject=$true
  $rejected=$false
  try { Assert-Managed-Container "mangadvisor_postgres" "postgres" } catch { $rejected=$true }
  if (-not $rejected) { throw "Foreign Docker Compose project was accepted." }
  $script:wrongProject=$false
  $rejected=$false
  try { Assert-Managed-Container "mangadvisor_postgres" "meilisearch" } catch { $rejected=$true }
  if (-not $rejected) { throw "Wrong Docker Compose service was accepted." }

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
  # 5. Authentication mismatch in persisted PGDATA must not be "fixed"
  # without an already verified dump and a second explicit owner approval.
  $script:containerExists=$true
  $script:loginFixed=$false
  $verified=Join-Path $script:backups "mangadvisor_20261022_163000_deadbeef.dump"
  [IO.File]::WriteAllText($verified,("backupfixture" * 20),[Text.Encoding]::ASCII)
  $hash=(Get-FileHash -LiteralPath $verified -Algorithm SHA256).Hash.ToLowerInvariant()
  @{
    file="mangadvisor_20261022_163000_deadbeef.dump"
    database="mangadvisor"
    sha256=$hash
  } | ConvertTo-Json | Set-Content -LiteralPath "$verified.json" -Encoding UTF8
  if (Test-Api-Password) { throw "The PGDATA password mismatch was missed." }
  $script:NonInteractive=$true
  $rejected=$false
  try { Repair-Api-PasswordAfterBackup $verified } catch { $rejected=$true }
  if (-not $rejected -or $script:loginFixed) {
    throw "Noninteractive secret rotation must be forbidden."
  }
  $script:NonInteractive=$false
  function Read-Host([string]$Prompt) { return "NO" }
  $rejected=$false
  try { Repair-Api-PasswordAfterBackup $verified } catch { $rejected=$true }
  if (-not $rejected -or $script:loginFixed) { throw "Denied password change was performed." }
  function Read-Host([string]$Prompt) { return "REPARER" }
  Repair-Api-PasswordAfterBackup $verified
  if (-not $script:loginFixed -or -not (Test-Api-Password)) {
    throw "Confirmed repair did not enable authenticated TCP access."
  }
  $count=@($script:commands | Where-Object { $_ -match '^exec -i mangadvisor_postgres psql ' }).Count
  if ($count -ne 1) { throw "Expected exactly one role-secret rotation." }
  if (($script:commands -join " ") -match "ORIGINAL_SECRET_FROM_CONTAINER") {
    throw "A PostgreSQL secret was exposed as a Docker CLI argument."
  }
  Write-Host "OK: stopped-container recovery, owner refusal, secret preservation, no recreation, missing-container blockade, authenticated TCP repair after verified dump."
} finally {
  Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
}
