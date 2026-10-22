# Offline Windows PowerShell 5.1: absent PostgreSQL container, existing PGDATA.
# Never contacts a real Docker daemon, private data or production volume.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$folder=Join-Path $env:RUNNER_TEMP ("ma_volume_recovery_"+[guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$script:envFile=Join-Path $folder ".env"
$script:backups=Join-Path $folder "backups"
$script:containerName="mangadvisor_postgres"
$script:compose=@("--env-file",$script:envFile,"-f","dummy.yml")
$script:NonInteractive=$false
$script:volumeExists=$true
$script:otherContainer=$false
$script:containerExists=$false
$script:pgdataValid=$true
$script:foreignVolume=$false
$script:validMount=$true
$script:approved="NON"
$script:composeCount=0
$script:commands=New-Object "System.Collections.Generic.List[string]"
New-Item -ItemType Directory -Force -Path $script:backups | Out-Null
[IO.File]::WriteAllText($script:envFile,"POSTGRES_DB=mangadvisor"+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))

$backup=Join-Path $script:backups "mangadvisor_20261022_165500_ba5eba11.dump"
[IO.File]::WriteAllText($backup,("synthetic" * 30),[Text.Encoding]::ASCII)
$hash=(Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash.ToLowerInvariant()
@{file=(Split-Path -Leaf $backup);database="mangadvisor";sha256=$hash} |
  ConvertTo-Json | Set-Content -LiteralPath "$backup.json" -Encoding UTF8

$source=Join-Path $PSScriptRoot "..\..\cmd\library-backup.ps1"
$tokens=$null
$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw "Main backup script contains invalid PowerShell." }
$functions=@($ast.FindAll({
  param($node)
  $node -is [Management.Automation.Language.FunctionDefinitionAst]
},$false))
foreach ($name in @("Assert-Ok","Config-Setting","Assert-Recovery-Backup","Recover-Missing-Postgres")) {
  $matches=@($functions | Where-Object { $_.Name -ceq $name })
  if ($matches.Count -ne 1) { throw "Missing or duplicate function $name" }
  Invoke-Expression $matches[0].Extent.Text
}
function Read-Host([string]$message) { return $script:approved }
function Container-Exists([string]$name) { return $script:containerExists }
function Assert-Managed-Container([string]$name,[string]$service) {
  if (-not $script:containerExists -or $name -cne "mangadvisor_postgres" -or
      $service -cne "postgres") { throw "Recreated container identity mismatch." }
}
function docker {
  $argv=@($args)
  $script:commands.Add(($argv -join " "))
  $global:LASTEXITCODE=0
  if ($argv[0] -eq "context" -and $argv[1] -eq "show") { "desktop-linux"; return }
  if ($argv[0] -eq "volume" -and $argv[1] -eq "ls") {
    if ($script:volumeExists) { "mangadvisor_mangadvisor_pgdata" }
    return
  }
  if ($argv[0] -eq "volume" -and $argv[1] -eq "inspect") {
    if ($script:foreignVolume) {
      '{"com.docker.compose.project":"another-project","com.docker.compose.volume":"mangadvisor_pgdata"}'
    } else {
      '{"com.docker.compose.project":"mangadvisor","com.docker.compose.volume":"mangadvisor_pgdata"}'
    }
    return
  }
  if ($argv[0] -eq "container" -and $argv[1] -eq "ls") {
    if ($script:otherContainer) { "an_existing_postgres_process" }
    return
  }
  if ($argv[0] -eq "image" -and $argv[1] -eq "ls") { "pgvector/pgvector:pg16"; return }
  if ($argv[0] -eq "run") {
    if (-not $script:pgdataValid) { $global:LASTEXITCODE=1 }
    return
  }
  if ($argv[0] -eq "compose") {
    if ($script:containerExists) { throw "A second database was started." }
    $script:composeCount++
    $script:containerExists=$true
    return
  }
  if ($argv[0] -eq "container" -and $argv[1] -eq "inspect") {
    $format=[string]$argv[3]
    if ($format -cne "{{json .Mounts}}") { throw "Unexpected Docker template." }
    if ($script:validMount) {
      '[{"Type":"volume","Name":"mangadvisor_mangadvisor_pgdata","Destination":"/var/lib/postgresql/data"}]'
    } else {
      '[{"Type":"volume","Name":"wrong_pgdata","Destination":"/var/lib/postgresql/data"}]'
    }
    return
  }
  throw "Unknown Docker command $($argv -join ' ')"
}
function Expect-Blocked([string]$description) {
  $old=$script:composeCount
  $blocked=$false
  try { Recover-Missing-Postgres } catch { $blocked=$true }
  if (-not $blocked) { throw "Expected safe refusal: $description" }
  if ($script:composeCount -ne $old) { throw "Compose started despite refusal: $description" }
}
try {
  $script:volumeExists=$false
  Expect-Blocked "missing volume"
  $script:volumeExists=$true
  $script:otherContainer=$true
  Expect-Blocked "volume already mounted"
  $script:otherContainer=$false
  $script:foreignVolume=$true
  Expect-Blocked "wrong Compose project"
  $script:foreignVolume=$false
  $script:pgdataValid=$false
  Expect-Blocked "no valid PG_VERSION"
  $script:pgdataValid=$true

  $infoFile="$backup.json"
  $metadata=[IO.File]::ReadAllText($infoFile)
  [IO.File]::WriteAllText($infoFile,$metadata.Replace($hash,('0' * 64)))
  Expect-Blocked "tampered backup manifest"
  [IO.File]::WriteAllText($infoFile,$metadata)

  $script:NonInteractive=$true
  Expect-Blocked "automatic creation forbidden"
  $script:NonInteractive=$false
  $script:approved="NON"
  Expect-Blocked "owner refusal"
  $script:approved="RECUPERER"
  Recover-Missing-Postgres
  if (-not $script:containerExists -or $script:composeCount -ne 1) {
    throw "Approved recovery not performed exactly once."
  }
  $commands=($script:commands -join [Environment]::NewLine)
  if ($commands -match '(?m)^compose .* down|(?m)^volume rm|(?m)^rm -f|(?m)^compose .* --force-recreate') {
    throw "Destructive Docker operation attempted."
  }
  if ($commands -notmatch 'run --rm --pull never --network none --read-only --mount') {
    throw "PGDATA not checked through a read-only mount."
  }
  Write-Host "OK: missing container, historical volume, backup SHA, consent and no destructive actions."
} finally {
  Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue
}
