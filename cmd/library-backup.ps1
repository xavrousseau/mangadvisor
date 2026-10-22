# Mangadvisor 3.2: consistent PostgreSQL backups, SHA256, isolated restore.
# Windows PowerShell 5.1 and PowerShell 7. Binary files via docker cp ONLY.
param(
  [ValidateSet("Backup","Verify","Restore")][string]$Action="Backup",
  [string]$File="",
  [switch]$NonInteractive,
  [switch]$CiRestore
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile=Join-Path $root ".env"
$backups=Join-Path $root "backups"
$containerName="mangadvisor_postgres"
$compose=@("--env-file",$envFile,
  "-f",(Join-Path $root "infra/compose/docker-compose.yml"),
  "-f",(Join-Path $root "infra/compose/docker-compose.local.yml"))

function Assert-Ok([string]$message) {
  if ($LASTEXITCODE -ne 0) { throw "$message (code $LASTEXITCODE)" }
}
function Run-Docker([string[]]$CommandArgs, [string]$Message) {
  # Never leak Docker stdout into the PowerShell function return value.
  & docker @CommandArgs | Out-Null
  Assert-Ok $Message
}
function Container-Exists([string]$name) {
  # Missing docker objects must not produce fatal NativeCommandError on PS 5.1.
  $names=@(& docker container ls -a --format "{{.Names}}")
  Assert-Ok "Liste des conteneurs Docker indisponible"
  return ($names -contains $name)
}
function Installed-Setting([string]$container,[string]$key) {
  # Docker keeps the original service configuration even while stopped.
  # This reads it IN MEMORY only. Never print password values.
  $entries=@(& docker container inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $container)
  Assert-Ok "Lecture de la configuration du conteneur impossible"
  $prefix=$key+"="
  $matches=@($entries | Where-Object { ([string]$_).StartsWith($prefix,[StringComparison]::Ordinal) })
  if ($matches.Count -ne 1) {
    throw "Variable $key absente ou dupliquee dans le conteneur $container. Aucune restauration de secret."
  }
  $value=([string]$matches[0]).Substring($prefix.Length)
  if (-not $value -or $value.Contains("`n") -or $value.Contains("`r")) {
    throw "Valeur $key non exploitable dans le conteneur $container."
  }
  return $value
}
function Config-Setting([string]$key) {
  $lines=@(Get-Content -LiteralPath $envFile -Encoding UTF8 | Where-Object {
    $_ -match ("^\s*" + [regex]::Escape($key) + "\s*=")
  })
  if ($lines.Count -ne 1) { throw "Configuration privee $key absente ou dupliquee." }
  return ([string]$lines[0]).Split("=",2)[1].Trim().Trim("'").Trim('"')
}
function Assert-Managed-Container([string]$container,[string]$service) {
  $format='{{index .Config.Labels "com.docker.compose.service"}}'
  $actual=@(& docker container inspect --format $format $container)
  Assert-Ok "Impossible de verifier le service Docker $container"
  if ($actual.Count -ne 1 -or ([string]$actual[0]).Trim() -cne $service) {
    throw "Conteneur $container inconnu ou non gere par Compose ($service attendu). Stop : aucun volume remplace."
  }
  $project=@(& docker container inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' $container)
  Assert-Ok "Impossible de verifier le projet Docker"
  if ($project.Count -ne 1 -or ([string]$project[0]).Trim() -cne "mangadvisor") {
    throw "Le conteneur $container appartient a un autre projet. Sauvegarde annulee."
  }
}
function Repair-Installed-Environment {
  if (-not (Container-Exists $containerName)) {
    throw "Le conteneur PostgreSQL $containerName est absent. Refus de creer une base vide pendant la sauvegarde. Verifier docker ps -a et les volumes."
  }
  Assert-Managed-Container $containerName "postgres"
  $installed=@{}
  foreach ($key in @("POSTGRES_DB","POSTGRES_USER","POSTGRES_PASSWORD")) {
    $installed[$key]=Installed-Setting $containerName $key
  }
  $meiliName="mangadvisor_meilisearch"
  if (Container-Exists $meiliName) {
    Assert-Managed-Container $meiliName "meilisearch"
    $installed["MEILI_MASTER_KEY"]=Installed-Setting $meiliName "MEILI_MASTER_KEY"
  } else {
    # A previously persisted Meilisearch index may depend on its old key.
    $volumes=@(& docker volume ls --format "{{.Name}}")
    Assert-Ok "Liste des volumes Docker indisponible"
    if ($volumes -contains "mangadvisor_mangadvisor_meili") {
      throw "Ancien volume Meilisearch present sans conteneur correspondant. Ne pas appliquer une nouvelle cle automatiquement."
    }
  }
  $different=@($installed.Keys | Where-Object { (Config-Setting $_) -cne $installed[$_] } | Sort-Object)
  if ($different.Count -eq 0) {
    Write-Host "Configuration locale : identique aux conteneurs existants."
    return
  }
  Write-Host ""
  Write-Warning ("Le fichier .env differe des conteneurs existants pour : " + ($different -join ", "))
  Write-Host "Cela peut arriver si .env a ete recree pendant que les volumes etaient preserves."
  Write-Host "Les identifiants ne seront PAS affiches. Une copie de .env sera conservee dans backups/configuration."
  if ($NonInteractive -or -not (Confirm-Repair "Restaurer la configuration des conteneurs existants dans .env ?")) {
    throw "Configuration incoherente : restauration refusee. Aucune suppression de donnees ni de volumes."
  }
  $raw=[IO.File]::ReadAllText($envFile,[Text.Encoding]::UTF8)
  $updated=$raw
  foreach ($key in $different) {
    $pattern="(?m)^" + [regex]::Escape($key) + "=.*$"
    if ([regex]::Matches($updated,$pattern).Count -ne 1) {
      throw "Configuration $key invalide : restauration annulee."
    }
    $updated=[regex]::Replace($updated,$pattern,
      [System.Text.RegularExpressions.MatchEvaluator]{
        param($m)
        return $key+"="+$installed[$key]
      })
  }
  $folder=Join-Path $backups "configuration"
  if (-not (Test-Path -LiteralPath $folder)) {
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
  }
  $tag=(Get-Date -Format "yyyyMMdd_HHmmss") + "_" + ([guid]::NewGuid().ToString("N")).Substring(0,8)
  $saved=Join-Path $folder (".env_before_recovery_" + $tag)
  Copy-Item -LiteralPath $envFile -Destination $saved -ErrorAction Stop
  # Write the replacement as a private temporary file on the same filesystem,
  # then replace the original. Never output the contents to stdout or Git.
  $temp=Join-Path $folder (".env_repaired_" + $tag)
  try {
    [IO.File]::WriteAllText($temp,$updated,(New-Object Text.UTF8Encoding($false)))
    Copy-Item -LiteralPath $temp -Destination $envFile -Force -ErrorAction Stop
  } catch {
    Copy-Item -LiteralPath $saved -Destination $envFile -Force
    throw "Impossible de restaurer .env : configuration initiale conservee. $($_.Exception.Message)"
  } finally {
    Remove-Item -LiteralPath $temp -ErrorAction SilentlyContinue
  }
  Write-Host ("Configuration des conteneurs restauree. Copie de securite : backups/configuration/" + (Split-Path -Leaf $saved))
}
function Confirm-Repair([string]$Question) {
  $response=Read-Host "$Question (o/N)"
  return $response -match '^(o|oui|y|yes)$'
}
function Prepare-Existing-Postgres {
  # Never invoke 'compose up' before the CURRENT database is backed up:
  # with changed secrets, Compose could recreate the old container.
  Repair-Installed-Environment
  $state=@(& docker container inspect --format "{{.State.Running}}" $containerName)
  Assert-Ok "Etat de PostgreSQL illisible"
  if ($state.Count -ne 1) { throw "Etat de PostgreSQL inattendu." }
  if (([string]$state[0]).Trim() -cne "true") {
    Write-Host "PostgreSQL est arrete. Redemarrage du conteneur existant, sans recreation."
    Run-Docker @("start",$containerName) "Impossible de redemarrer PostgreSQL existant"
  }
  $pgUser=Installed-Setting $containerName "POSTGRES_USER"
  $pgDb=Installed-Setting $containerName "POSTGRES_DB"
  $ready=$false
  for ($attempt=0; $attempt -lt 40; $attempt++) {
    & docker exec $containerName pg_isready -U $pgUser -d $pgDb 1>$null 2>$null
    if ($LASTEXITCODE -eq 0) { $ready=$true; break }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) { throw "PostgreSQL existant ne demarre pas. Lire ses logs Docker, ne supprimer aucun volume." }
  # pg_isready alone does not prove that a newly recreated environment
  # can authenticate against an OLD persisted PostgreSQL cluster.
  $test=@(& docker exec $containerName sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -X -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1"' 2>$null)
  if ($LASTEXITCODE -ne 0 -or $test.Count -ne 1 -or ([string]$test[0]).Trim() -ne "1") {
    throw "Identifiants du conteneur incompatibles avec la base PostgreSQL existante. Refus de la sauvegarde/mise a jour : recuperer les anciens identifiants."
  }
  Write-Host "PostgreSQL existant actif, configuration reconnue et connexion authentifiee."
}
function Db-Setting([string]$key) {
  $result=& docker exec $containerName printenv $key
  Assert-Ok "Configuration PostgreSQL $key indisponible"
  return ([string]$result).Trim()
}
function Admin-Sql([string]$sql) {
  $result=& docker exec $containerName psql -X -v ON_ERROR_STOP=1 -U $script:pgUser -d postgres -At -c $sql
  Assert-Ok "Echec SQL de maintenance"
  return ($result -join [Environment]::NewLine).Trim()
}
function Token { return ([guid]::NewGuid().ToString("N")).Substring(0,8) }
function Backup-Path([string]$given) {
  if (-not (Test-Path $backups)) { throw "Aucun dossier de sauvegarde." }
  if (-not $given) {
    $latest=Get-ChildItem -LiteralPath $backups -Filter "mangadvisor_*.dump" -File |
      Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($null -eq $latest) { throw "Aucune sauvegarde." }
    $given=$latest.FullName
  }
  $path=[IO.Path]::GetFullPath($given)
  if ([IO.Path]::GetFullPath((Split-Path -Parent $path)) -ne [IO.Path]::GetFullPath($backups) -or
      (Split-Path -Leaf $path) -notmatch '^mangadvisor_[0-9]{8}_[0-9]{6}_[a-f0-9]{8}\.dump$') {
    throw "Seuls les fichiers du dossier backups/ sont acceptes."
  }
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Sauvegarde absente." }
  if (-not (Test-Path -LiteralPath "$path.json" -PathType Leaf)) { throw "Manifeste absent." }
  $meta=Get-Content -LiteralPath "$path.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($meta.file -cne (Split-Path -Leaf $path) -or $meta.database -cne $script:pgDb) {
    throw "La sauvegarde ne correspond pas a la base actuelle."
  }
  $sha=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($sha -cne $meta.sha256) { throw "Archive corrompue ou modifiee (SHA256)." }
  if ((Get-Item -LiteralPath $path).Length -lt 100) { throw "Archive invalide." }
  return $path
}
function Drop-Verification([string]$name) {
  if ($name -notmatch '^ma_verify_[a-f0-9]{8}$') { throw "Base de verification invalide." }
  Run-Docker @("exec",$containerName,"dropdb","--if-exists","--force","-U",$script:pgUser,$name) "Echec nettoyage base de verification"
}
function Restore-Test([string]$archive,[switch]$KeepDatabase) {
  # Uses a fresh isolated database, never the live Mangadvisor database.
  $testDb="ma_verify_$(Token)"
  $remote="/tmp/ma_check_$(Token).dump"
  $created=$false
  try {
    Run-Docker @("cp",$archive,("{0}:{1}" -f $containerName,$remote)) "Copie binaire impossible"
    Run-Docker @("exec",$containerName,"createdb","-U",$script:pgUser,"-T","template0",$testDb) "Creation base de verification impossible"
    $created=$true
    Run-Docker @("exec",$containerName,"pg_restore","-U",$script:pgUser,
      "--exit-on-error","--single-transaction","--no-owner","--no-acl",
      "-d",$testDb,$remote) "Restauration de test PostgreSQL echouee"
    $found=& docker exec $containerName psql -X -v ON_ERROR_STOP=1 -U $script:pgUser -d $testDb -At -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename IN ('manga','user_manga_library','manga_fr_edition','user_manga_volume');"
    Assert-Ok "Verification du schema echouee"
    if (([string]$found).Trim() -ne "4") { throw "Tables essentielles absentes du fichier restaure." }
    $counts=& docker exec $containerName psql -X -v ON_ERROR_STOP=1 -U $script:pgUser -d $testDb -At -c "SELECT (SELECT count(*) FROM manga)||' mangas; '||(SELECT count(*) FROM user_manga_library)||' suivis; '||(SELECT count(*) FROM manga_fr_edition)||' ISBN; '||(SELECT count(*) FROM user_manga_volume)||' tomes suivis';"
    Assert-Ok "Lecture des donnees restaurees impossible"
    Write-Host "Restauration de test validee : $counts"
    # Work-level reading statuses and owner-declared physical inventory are
    # different tables. Checking only user_manga_library can hide possessions.
    foreach ($table in @("user_manga_inventory_declaration","user_manga_inventory_pending")) {
      $exists=& docker exec $containerName psql -X -v ON_ERROR_STOP=1 -U $script:pgUser -d $testDb -At -c "SELECT CASE WHEN to_regclass('public.$table') IS NOT NULL THEN 1 ELSE 0 END;"
      Assert-Ok "Impossible de verifier la presence de la table $table"
      if (([string]$exists).Trim() -eq "1") {
        $count=& docker exec $containerName psql -X -v ON_ERROR_STOP=1 -U $script:pgUser -d $testDb -At -c "SELECT count(*) FROM $table;"
        Assert-Ok "Impossible de verifier les declarations dans $table"
        Write-Host ("  {0}: {1} lignes restaurees" -f $table,([string]$count).Trim())
      } else {
        Write-Host ("  {0}: table absente de cette archive ancienne" -f $table)
      }
    }
    if ($KeepDatabase) { $created=$false; return $testDb }
  }
  finally {
    if ($created) { Drop-Verification $testDb }
    & docker exec $containerName rm -f $remote | Out-Null
  }
}
function Create-Backup {
  if (-not (Test-Path $backups)) { New-Item -ItemType Directory -Path $backups -Force | Out-Null }
  $filename="mangadvisor_$(Get-Date -Format 'yyyyMMdd_HHmmss')_$(Token).dump"
  $local=Join-Path $backups $filename
  $remote="/tmp/ma_dump_$(Token).dump"
  try {
    Write-Host "Sauvegarde PostgreSQL coherente en cours..."
    Run-Docker @("exec",$containerName,"pg_dump","-U",$script:pgUser,"-d",$script:pgDb,"-Fc","-Z","6","-f",$remote) "pg_dump echoue"
    & docker exec $containerName pg_restore --list $remote | Out-Null
    Assert-Ok "Archive produite invalide"
    Run-Docker @("cp",("{0}:{1}" -f $containerName,$remote),$local) "Copie du fichier echouee"
    $manifest=[ordered]@{
      format="mangadvisor-pg-custom-v1"
      file=$filename
      database=$script:pgDb
      created_at=(Get-Date).ToUniversalTime().ToString("o")
      bytes=(Get-Item -LiteralPath $local).Length
      sha256=(Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath "$local.json" -Encoding UTF8
    Write-Host "Fichier: $local"
    Write-Host "Empreinte SHA256: $($manifest.sha256)"
    $null=Restore-Test (Backup-Path $local)
    Write-Host "Sauvegarde terminee et restauration de test reussie."
    return $local
  }
  finally { & docker exec $containerName rm -f $remote | Out-Null }
}
if (-not (Test-Path -LiteralPath $envFile)) { throw "Fichier .env manquant." }
& docker info --format "{{.ServerVersion}}" | Out-Null
Assert-Ok "Docker Desktop doit etre demarre"
$pgDb=Db-Setting "POSTGRES_DB"
$pgUser=Db-Setting "POSTGRES_USER"
if ($pgDb -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$' -or $pgDb -in @("postgres","template0","template1")) {
  throw "Nom de base PostgreSQL non valide pour une restauration."
}
if ($Action -eq "Backup") { $null=Create-Backup; exit 0 }
$archive=Backup-Path $File
if ($Action -eq "Verify") { $null=Restore-Test $archive; exit 0 }

# Live restore is NEVER automatic. Keep the old database, do not drop it.
if ($NonInteractive -and -not ($CiRestore -and $env:MANGADVISOR_BACKUP_TEST_CI -eq "1" -and $pgDb -eq "mangadvisor_ci")) {
  throw "Restauration de production refusee en mode non interactif."
}
if ($CiRestore -and -not ($env:MANGADVISOR_BACKUP_TEST_CI -eq "1" -and $pgDb -eq "mangadvisor_ci")) {
  throw "Mode CI reserve a la base de test jetable."
}
Write-Host "ATTENTION : remplacement de la base active $pgDb."
Write-Host "L'ancienne base sera conservee sous un autre nom et sur le meme volume Docker."
if (-not $CiRestore) {
  $typed=Read-Host "Saisir exactement RESTAURER $pgDb"
  if ($typed -cne "RESTAURER $pgDb") { throw "Operation annulee sans modification." }
}
$restoredDb=$null
$oldDb="ma_before_$(Token)"
$renamedOld=$false
$swapped=$false
$catalogWorkerWasRunning=$false
try {
  # Verify an independent safety copy of the CURRENT database before switching.
  $null=Create-Backup
  $restoredDb=Restore-Test $archive -KeepDatabase
  # The opt-in daily worker writes the same PostgreSQL database. Suspend it
  # BEFORE swapping the live DB name, otherwise it may reconnect mid-restore.
  $workerState=@(& docker inspect --format "{{.State.Running}}" mangadvisor_catalog_sync 2>$null)
  if ($LASTEXITCODE -eq 0 -and $workerState.Count -gt 0 -and
      ([string]$workerState[0]).Trim() -eq "true") {
    & docker compose @compose --profile automation stop catalog-sync
    Assert-Ok "Impossible de suspendre le catalogue automatique : restauration annulee"
    $catalogWorkerWasRunning=$true
    Write-Host "Synchronisation automatique arretee pour securiser la restauration."
  }
  & docker compose @compose stop api web engine
  Assert-Ok "Impossible d'arreter les services applicatifs"
  $null=Admin-Sql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$pgDb' AND pid<>pg_backend_pid();"
  $q=[char]34
  $null=Admin-Sql ("ALTER DATABASE {0}{1}{0} RENAME TO {0}{2}{0};" -f $q,$pgDb,$oldDb)
  $renamedOld=$true
  $null=Admin-Sql ("ALTER DATABASE {0}{1}{0} RENAME TO {0}{2}{0};" -f $q,$restoredDb,$pgDb)
  $swapped=$true
  $restoredDb=$null
}
catch {
  if ($renamedOld -and -not $swapped) {
    Write-Warning "Basculement interrompu, restauration de l'ancien nom."
    $q=[char]34
    $null=Admin-Sql ("ALTER DATABASE {0}{1}{0} RENAME TO {0}{2}{0};" -f $q,$oldDb,$pgDb)
  }
  throw
}
finally {
  if ($restoredDb) { Drop-Verification $restoredDb }
  # Restart only the single supported Web site at 8501.
  & docker compose @compose up -d api web
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Relancer mangadvisor.cmd option 3 pour les services Web."
  } elseif ($swapped -and $catalogWorkerWasRunning) {
    & docker compose @compose --profile automation up -d --no-deps catalog-sync
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Veille arretee : reactiver depuis mangadvisor.cmd, A puis 21."
    } else {
      Write-Host "Synchronisation du catalogue relancee apres restauration validee."
    }
  } elseif ($catalogWorkerWasRunning) {
    Write-Warning "Restauration interrompue : veille maintenue arretee par securite."
  }
}
Write-Host "Restauration reussie. Ancienne base toujours disponible sous le nom: $oldDb"
