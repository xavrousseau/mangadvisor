# Export the PUBLIC Mangadvisor catalogue only. Never export owner inventory.
# PS 5.1 compatible; binary archives only via docker cp (not PowerShell pipes).
param([switch]$SkipRaw)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
Assert-MangadvisorStableCheckout $root

$container = "mangadvisor_postgres"
$output = Join-Path $root "backups\catalogue-public"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$token = ([guid]::NewGuid().ToString("N")).Substring(0,8)
$exportName = "catalogue_$($stamp)_$token"
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker introuvable."
}

function Assert-Command([string]$message) {
    if ($LASTEXITCODE -ne 0) { throw "$message (code $LASTEXITCODE)" }
}
function Require-ManagedPostgres {
    # Read only Docker labels. No username/password displayed.
    $raw = @(& docker container inspect --format '{{json .Config.Labels}}' $container)
    Assert-Command "Le conteneur PostgreSQL Mangadvisor est absent."
    if ($raw.Count -ne 1) { throw "Impossible de lire les etiquettes du conteneur." }
    $labels = ConvertFrom-Json ([string]$raw[0])
    if ($labels.'com.docker.compose.project' -cne "mangadvisor" -or
        $labels.'com.docker.compose.service' -cne "postgres") {
        throw "Ce n'est pas le conteneur PostgreSQL Mangadvisor officiel."
    }
    $status = @(& docker inspect --format '{{.State.Running}}' $container)
    Assert-Command "Impossible de lire l'etat Docker."
    if ($status.Count -ne 1 -or [string]$status[0] -cne "true") {
        throw "Demarre Mangadvisor (option 2) avant d'exporter son catalogue."
    }
}
function DbEnv([string]$name) {
    $lines = @(& docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $container)
    Assert-Command "Lecture de la configuration PostgreSQL impossible."
    $matches = @($lines | Where-Object {
        ([string]$_).StartsWith($name + "=", [StringComparison]::Ordinal)
    })
    if ($matches.Count -ne 1) { throw "$name introuvable dans le conteneur." }
    $value = ([string]$matches[0]).Substring($name.Length + 1)
    if ($value -notmatch '^[a-zA-Z_][a-zA-Z_0-9]{0,62}$') {
        throw "Nom $name invalide : export annule."
    }
    return $value
}
function Run-Psql([string]$query) {
    $result = @(& docker exec $container psql -X -v ON_ERROR_STOP=1 -U $script:dbUser -d $script:dbName -At -c $query)
    Assert-Command "Lecture SQL impossible ; aucune modification effectuee."
    return $result
}
function Write-PublicDump([string]$name,[string[]]$tables) {
    if ($tables.Count -eq 0) { return $null }
    $remote = "/tmp/mangadvisor_public_$token" + "_$name.dump"
    $local = Join-Path $output ($exportName + "_" + $name + ".dump")
    $args = @("exec",$container,"pg_dump","-U",$script:dbUser,"-d",$script:dbName,
              "-Fc","-Z","6","--no-owner","--no-privileges","-f",$remote)
    foreach ($table in $tables) {
        # PowerShell 5.1 may flatten `@("-t","public." + $table)` into
        # three native argv elements: -t, public., manga. PostgreSQL then
        # treats "manga" as an unexpected positional database argument.
        # Build ONE atomic --table=... argument per public table.
        $args += ("--table=public." + [string]$table)
    }
    Write-Host ("Extraction publique : " + $name + " (" + $tables.Count + " tables)")
    try {
        & docker @args | Out-Null
        Assert-Command "pg_dump a echoue"
        & docker exec $container pg_restore -l $remote | Out-Null
        Assert-Command "Archive PostgreSQL non lisible"
        & docker cp ($container + ":" + $remote) $local | Out-Null
        Assert-Command "Copie locale de l'archive impossible"
        if (!(Test-Path -LiteralPath $local -PathType Leaf) -or
            (Get-Item -LiteralPath $local).Length -le 0) {
            throw "Archive vide ou absente : $local"
        }
        $file = Get-Item -LiteralPath $local
        $sha = (Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash.ToLowerInvariant()
        return @{
            filename=$file.Name
            bytes=$file.Length
            sha256=$sha
            tables=$tables
        }
    } finally {
        # Only remove the temp export inside the container, never volumes.
        & docker exec $container rm -f $remote | Out-Null
    }
}

Require-ManagedPostgres
$script:dbUser = DbEnv "POSTGRES_USER"
$script:dbName = DbEnv "POSTGRES_DB"

# Deliberately explicit allowlist. NO table beginning with user_, private_
# or any personal collection / reading history / secret table can enter.
$publicTables = @(
    "manga","genre","manga_genre","theme","manga_theme",
    "demographic","manga_demographic",
    "manga_title_alias","manga_title_alias_attempt",
    "manga_wikidata_fact","manga_wikidata_attempt",
    "manga_scrinis_fr_fact","manga_scrinis_fr_attempt",
    "manga_mangaupdates_evidence","manga_mangaupdates_attempt",
    "manga_bnf_candidate","manga_bnf_attempt",
    "manga_fr_edition","manga_fr_edition_group",
    "manga_fr_edition_group_book"
)
# Validate table existence before pg_dump. Optional older tables are skipped.
$sql = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
$found = @(Run-Psql $sql)
if ($found -notcontains "manga" -or $found -notcontains "jikan_manga_source") {
    throw "Catalogue principal incomplet. Exporte uniquement depuis la base stable."
}
$selected = @($publicTables | Where-Object { $found -contains $_ })
$missing = @($publicTables | Where-Object { $found -notcontains $_ })
if (!(Test-Path -LiteralPath $output)) {
    New-Item -ItemType Directory -Path $output -Force | Out-Null
}
$archiveRecords = @()
$main = Write-PublicDump "metadata" $selected
if ($null -eq $main) { throw "Aucune archive metadata produite." }
$archiveRecords += $main
if (!$SkipRaw) {
    $raw = Write-PublicDump "jikan_raw" @("jikan_manga_source")
    if ($null -ne $raw) { $archiveRecords += $raw }
}

# A small, standalone metadata report helps initial diagnosis and integrity.
$rows = @()
foreach ($table in $selected) {
    $quantity = @(
        Run-Psql ('SELECT count(*) FROM public."' + $table + '";')
    )
    if ($quantity.Count -ne 1) { throw "Compte invalide pour $table" }
    $rows += @{ table=$table; rows=[long]$quantity[0] }
}
$rawCount = @(Run-Psql 'SELECT count(*) FROM public.jikan_manga_source;')
$rows += @{ table="jikan_manga_source"; rows=[long]$rawCount[0] }
# Global health indicators computed over the ENTIRE public catalogue.
# Counts are diagnostic signals, never automatic reasons to merge works.
$quality = @()
$probes = @(
    @{key="canonical_work_without_raw_mal"; needs=@("manga");
      sql="SELECT count(*) FROM manga m LEFT JOIN jikan_manga_source j ON j.mal_id=m.source_mal_id WHERE j.mal_id IS NULL;"},
    @{key="raw_jikan_without_canonical_work"; needs=@("manga");
      sql="SELECT count(*) FROM jikan_manga_source j LEFT JOIN manga m ON m.source_mal_id=j.mal_id WHERE m.id IS NULL;"},
    @{key="manga_missing_original_title"; needs=@("manga");
      sql="SELECT count(*) FROM manga WHERE btrim(COALESCE(title,''))='';"},
    @{key="same_alias_used_for_multiple_works"; needs=@("manga_title_alias");
      sql="SELECT count(*) FROM (SELECT alias_key FROM manga_title_alias GROUP BY alias_key HAVING count(DISTINCT manga_id)>1) x;"},
    @{key="works_with_french_alias"; needs=@("manga_title_alias");
      sql="SELECT count(DISTINCT manga_id) FROM manga_title_alias WHERE language_code='fr';"},
    @{key="bnf_isbn_suggested_for_multiple_works"; needs=@("manga_bnf_candidate");
      sql="SELECT count(*) FROM (SELECT isbn13 FROM manga_bnf_candidate GROUP BY isbn13 HAVING count(DISTINCT manga_id)>1) x;"},
    @{key="bnf_isbn_candidate_count"; needs=@("manga_bnf_candidate");
      sql="SELECT count(*) FROM manga_bnf_candidate;"},
    @{key="registered_french_book_count"; needs=@("manga_fr_edition");
      sql="SELECT count(*) FROM manga_fr_edition;"},
    @{key="wikidata_mal_identity_mismatch"; needs=@("manga_wikidata_fact");
      sql="SELECT count(*) FROM manga_wikidata_fact f JOIN manga m ON m.id=f.manga_id WHERE f.source_mal_id<>m.source_mal_id;"}
)
foreach ($probe in $probes) {
    $notPresent=@($probe.needs | Where-Object { $selected -notcontains $_ })
    if ($notPresent.Count -gt 0) { continue }
    $result=@(Run-Psql $probe.sql)
    if ($result.Count -ne 1) { throw "Diagnostic invalide : $($probe.key)" }
    $quality += @{metric=$probe.key;value=[long]$result[0]}
}
$manifest = @{
    quality_indicators=$quality
    kind="Mangadvisor PUBLIC catalogue forensic export"
    exported_at_utc=[DateTime]::UtcNow.ToString("o")
    catalogue_only=$true
    includes_personal_library=$false
    includes_passwords=$false
    backups_unchanged=$true
    records=$rows
    archives=$archiveRecords
    unavailable_optional_tables=$missing
    read_only=$true
}
$manifestPath = Join-Path $output ($exportName + "_manifest.json")
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host ""
Write-Host "EXPORT PUBLIC DU CATALOGUE TERMINE" -ForegroundColor Green
Write-Host ("Dossier : " + $output)
Write-Host ("Fichier de controle : " + (Split-Path -Leaf $manifestPath))
foreach ($record in $archiveRecords) {
    Write-Host ("  " + $record.filename + "  (" +
       [math]::Round($record.bytes / 1MB, 1) + " Mo)")
}
Write-Host "Aucune table de mangatheque personnelle, aucun secret et aucune ecriture SQL."
Write-Host "Envoie les fichiers .dump et le _manifest.json dans la conversation."
