# Mangadvisor - single WEB deployment, stable default Compose stack.
# Requires PowerShell 5.1+, Docker Desktop; no Python installation on Windows.
# All database/catalog/recommendation jobs run in Docker; secrets stay in .env.
param(
  [ValidateSet("Environment","Database","Catalogue","Recommendations","Network","Diagnostic","Update","Wizard","Start","Stop")]
  [string]$Action="Wizard"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile=Join-Path $root ".env"
$example=Join-Path $root ".env.example"
$composeFiles=@("-f",(Join-Path $root "infra\compose\docker-compose.yml"),
                "-f",(Join-Path $root "infra\compose\docker-compose.local.yml"))

function Say([string]$Message) { Write-Host ""; Write-Host ("=== " + $Message + " ===") -ForegroundColor Cyan }
function Assert-Exit([string]$Message) {
  if ($LASTEXITCODE -ne 0) { throw "$Message (code $LASTEXITCODE)." }
}
function Run([string]$Program,[string[]]$Arguments,[string]$Failure) {
  & $Program @Arguments
  Assert-Exit $Failure
}
function Secret {
  $bytes=New-Object byte[] 28
  $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return [BitConverter]::ToString($bytes).Replace("-","").ToLowerInvariant()
}
function Config([string]$Key) {
  if (!(Test-Path -LiteralPath $envFile -PathType Leaf)) {
    throw "Fichier .env absent. Utilise mangadvisor.cmd, puis option 1 (premiere installation), pour le creer."
  }
  $found=@(Get-Content -LiteralPath $envFile | Where-Object {
    $_ -match ("^\s*" + [regex]::Escape($Key) + "\s*=")
  })
  if ($found.Count -eq 0) { throw "Variable $Key absente du fichier .env." }
  $value=([string]$found[-1]).Split("=",2)[1].Trim().Trim("'").Trim('"')
  if (-not $value) { throw "Variable $Key vide dans .env." }
  return $value
}
function Ensure-Environment {
  Say "Configuration privee et dossiers"
  if (!(Test-Path -LiteralPath $envFile)) {
    if (!(Test-Path -LiteralPath $example)) { throw ".env.example introuvable." }
    $template=[IO.File]::ReadAllText($example,[Text.Encoding]::UTF8)
    $pgSecret=Secret
    $meiliSecret=Secret
    $template=[regex]::Replace($template,"(?m)^POSTGRES_PASSWORD=.*$","POSTGRES_PASSWORD=$pgSecret")
    $template=[regex]::Replace($template,"(?m)^MEILI_MASTER_KEY=.*$","MEILI_MASTER_KEY=$meiliSecret")
    [IO.File]::WriteAllText($envFile,$template,(New-Object Text.UTF8Encoding($false)))
    Write-Host "Fichier .env cree avec deux secrets aleatoires differents."
  } else {
    Write-Host "Fichier .env existant conserve (aucun secret modifie)."
  }
  foreach ($key in @("POSTGRES_DB","POSTGRES_USER","POSTGRES_PASSWORD","POSTGRES_PORT",
                      "MEILI_MASTER_KEY","MEILI_PORT","API_PORT","UI_PORT","EMBEDDING_MODEL",
                      "ENABLE_TRANSLATION","ENABLE_OLLAMA","OLLAMA_PORT")) {
    $null=Config $key
  }
  if ((Config "POSTGRES_PASSWORD") -eq "changeme" -or
      (Config "MEILI_MASTER_KEY") -eq "changeme") {
    throw "Secrets non securises : remplace changeme dans .env puis recommence."
  }
  foreach ($folder in @("private-data","backups")) {
    $path=Join-Path $root $folder
    if (!(Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
  }
  Write-Host "Configuration prete. Ne publie jamais .env, private-data ou backups sur GitHub."
}
function Check-Docker {
  if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker absent. Installe Docker Desktop et demarre-le avant de continuer."
  }
  & docker info --format "{{.ServerVersion}}" 1>$null 2>$null
  Assert-Exit "Docker Desktop n'est pas demarre"
  & docker compose version
  Assert-Exit "Docker Compose indisponible"
}
function Compose([string[]]$Arguments) {
  $all=@("--env-file",$envFile)+$composeFiles+$Arguments
  $aiRaw=@(Get-Content -LiteralPath $envFile | Where-Object {
    $_ -like "OLLAMA_ENABLED=true"
  })
  if ($aiRaw.Count -gt 0) { $all=@("--profile","ai")+$all }
  Run "docker" (@("compose")+$all) "Echec de Docker Compose"
}
function Wait-Postgres {
  Say "Attente de PostgreSQL"
  for ($i=1;$i -le 40;$i++) {
    & docker exec mangadvisor_postgres pg_isready -U (Config "POSTGRES_USER") -d (Config "POSTGRES_DB") 1>$null 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "PostgreSQL pret."; return }
    Start-Sleep -Seconds 2
  }
  throw "PostgreSQL ne repond pas. Depuis les options avancees, choisis les journaux Docker."
}
function Sql-File([string]$RelativePath) {
  $source=Join-Path $root $RelativePath
  if (!(Test-Path -LiteralPath $source)) { throw "Script SQL absent : $RelativePath" }
  $remote="/tmp/mangadvisor_setup_$([guid]::NewGuid().ToString('N')).sql"
  try {
    Run "docker" @("cp",$source,("mangadvisor_postgres:"+$remote)) "Copie SQL impossible"
    Run "docker" @("exec","mangadvisor_postgres","psql","-X","-v","ON_ERROR_STOP=1",
                     "-U",(Config "POSTGRES_USER"),"-d",(Config "POSTGRES_DB"),
                     "-f",$remote) "Echec du script $RelativePath"
  } finally {
    & docker exec mangadvisor_postgres rm -f $remote 1>$null 2>$null
  }
}
function Initialize-Database {
  Say "Initialisation des tables SQL"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  foreach ($sql in @(
    "sql\schema\001_jikan_source_tables.sql",
    "sql\schema\002_canonical_manga_tables.sql",
    "sql\schema\004_add_theme_demographic_tables.sql",
    "sql\schema\006_add_jikan_recommendation_tables.sql",
    "sql\schema\007_add_user_library_tables.sql")) {
    Write-Host ("Application : " + $sql)
    Sql-File $sql
  }
  Write-Host "Tables initialisees. Operation additive : aucun volume efface."
}
function Start-Application([bool]$Build=$true) {
  Say "Demarrage des services Mangadvisor"
  Ensure-Environment
  Check-Docker
  # Turn off the old 8502 Streamlit UI, keeping data volumes untouched.
  # The user-friendly stack has no Streamlit service at all.
  # Retire an existing 8502 legacy container without removing its data or
  # touching the PostgreSQL/Meilisearch volumes.
  $devCompose=Join-Path $root "infra\compose\docker-compose.dev.yml"
  $legacyArgs=@("compose","--env-file",$envFile,
      "-f",(Join-Path $root "infra\compose\docker-compose.yml"),
      "-f",$devCompose,"--profile","legacy")
  Run "docker" ($legacyArgs+@("stop","ui")) "Impossible d'arreter l'ancienne interface"
  Run "docker" ($legacyArgs+@("rm","-f","ui")) "Impossible de retirer l'ancien conteneur UI"
  $args=@("up","-d")
  if ($Build) { $args+=@("--build") }
  Compose $args
  Write-Host ("Interface unique : http://localhost:" + (Config "UI_PORT"))
  Write-Host ("API       : http://localhost:" + (Config "API_PORT") + "/health")
}
function Open-Application {
  Say "Ouverture de Mangadvisor"
  Ensure-Environment
  Check-Docker
  # A simple everyday launch reuses existing images; do not download data again.
  # On first installation the guided wizard constructs everything with --build.
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  if ((Get-Count "manga") -eq 0) {
    throw "Catalogue absent ou vide. Lance d'abord l'option 1 (installation)."
  }
  Start-Application $false
  $null=Wait-Health
  $site="http://localhost:$(Config 'UI_PORT')"
  $resp=Invoke-RestMethod -Uri "$site/api/health" -TimeoutSec 15
  if ($resp.status -ne "ok") { throw "Le site ne parvient pas a joindre l'API." }
  Write-Host "Mangadvisor est pret : $site"
  try { Start-Process $site } catch {
    Write-Warning "Le navigateur ne s'est pas ouvert automatiquement. Adresse : $site"
  }
}
function Stop-Application {
  Say "Arret de Mangadvisor (donnees conservees)"
  Ensure-Environment
  Check-Docker
  Compose @("stop")
  Write-Host "Services arretes. Volumes PostgreSQL et fichiers prives conserves."
}
function Ask-Number([string]$Question,[int]$Default,[int]$Max) {
  $value=Read-Host "$Question [$Default]"
  if (-not $value) { return $Default }
  $n=0
  if (![int]::TryParse($value,[ref]$n) -or $n -lt 1 -or $n -gt $Max) {
    throw "Nombre invalide : choisir une valeur entre 1 et $Max."
  }
  return $n
}
function Confirm([string]$Question,[bool]$Default=$false) {
  $suffix=if($Default){"O/n"}else{"o/N"}
  $answer=Read-Host "$Question ($suffix)"
  if (-not $answer) { return $Default }
  return ($answer -match '^(o|oui|y|yes)$')
}
function Engine([string[]]$Arguments) {
  Compose (@("run","--rm","engine","python")+$Arguments)
}
function Network {
  Say "Diagnostic HTTPS Docker : fournisseur manga et acces Internet"
  Ensure-Environment
  Check-Docker
  Engine @("pipelines/engine/scripts/check_network.py")
}
function Get-Count([string]$Table) {
  $allowed=@("manga","jikan_manga_source","genre","manga_genre","theme","manga_theme",
             "demographic","manga_demographic","manga_recommendation_edge",
             "user_manga_inventory_declaration","user_manga_library","manga_fr_edition")
  if ($Table -notin $allowed) { throw "Table non autorisee." }
  # Pass every psql option as one native process invocation.
  # In Windows PowerShell, a bare newline before -U would split the command:
  # psql would connect as root, then PowerShell would try to execute '-U'.
  $psqlArgs=@("exec","mangadvisor_postgres","psql","-X","-At",
              "-v","ON_ERROR_STOP=1",
              "-U",(Config "POSTGRES_USER"),
              "-d",(Config "POSTGRES_DB"),
              "-c","SELECT COUNT(*) FROM $Table;")
  $result=@(& docker @psqlArgs 2>&1)
  Assert-Exit "Impossible d'interroger la table $Table. Initialiser d'abord les tables."
  $count=0
  if (![int]::TryParse(([string]$result[-1]).Trim(),[ref]$count)) {
    throw "Compteur invalide pour $Table."
  }
  return $count
}
function Load-Catalogue {
  Say "Alimentation du catalogue (Tenrai, compatible Jikan)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  $null=Get-Count "manga"
  Network
  $pages=Ask-Number "Nombre de pages SEARCH Tenrai (25 mangas/page)" 40 400
  $topPages=Ask-Number "Nombre de pages TOP Tenrai (25 mangas/page)" 10 100
  $force=Confirm "Actualiser aussi les fichiers JSON deja telecharges ?" $false
  $base=@("--start-page","1","--limit","25","--sleep-seconds","1","--no-legacy-search-copy")
  $search=@("pipelines/engine/scripts/extract_jikan.py","--mode","search")+
          $base+@("--end-page",[string]$pages,"--order-by","popularity","--sort","asc","--sfw","true")
  $top=@("pipelines/engine/scripts/extract_jikan.py","--mode","top")+
       $base+@("--end-page",[string]$topPages)
  if ($force) { $search+=@("--force");$top+=@("--force") }
  Engine $search
  Engine $top
  Engine @("pipelines/engine/scripts/load_jikan_to_postgres.py","--sources","search","top")
  foreach ($sql in @(
    "sql\schema\003_build_canonical_from_jikan.sql",
    "sql\schema\004_add_theme_demographic_tables.sql",
    "sql\schema\005_build_theme_demographic_from_jikan.sql")) {
    Sql-File $sql
  }
  $sourceCount=Get-Count "jikan_manga_source"
  $catalogCount=Get-Count "manga"
  Write-Host "Notices fournisseur : $sourceCount ; mangas dans le catalogue : $catalogCount"
  if ($catalogCount -eq 0) { throw "Catalogue vide : chargement Tenrai invalide." }
}
function Load-Recommendations {
  Say "Recommandations communautaires (Tenrai)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  if ((Get-Count "manga") -eq 0) { throw "Catalogue vide. Lance d'abord l'installation (1) ou actualise le catalogue (options avancees)." }
  Network
  $limit=Ask-Number "Nombre de mangas a enrichir" 50 2000
  $force=Confirm "Retelecharger les relations deja extraites ?" $false
  $argsList=@("pipelines/engine/scripts/extract_jikan_recommendations.py",
          "--limit-items",[string]$limit,"--sleep-seconds","1")
  if ($force) { $argsList+=@("--force") }
  Engine $argsList
  Engine @("pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py")
  $count=Get-Count "manga_recommendation_edge"
  Write-Host "Relations enregistrees : $count"
  if ($count -eq 0) {
    Write-Warning "Aucune relation en base : voir les logs d'extraction (le fournisseur peut renvoyer 0 resultat)."
  }
}
function Wait-Health {
  $uri="http://127.0.0.1:$(Config 'API_PORT')/health"
  for ($i=1;$i -le 20;$i++) {
    try {
      $data=Invoke-RestMethod -Uri $uri -TimeoutSec 5
      if ($data.status -eq "ok") { return $data }
    } catch {}
    Start-Sleep -Seconds 2
  }
  throw "API indisponible : $uri. Consulte les logs depuis le menu."
}
function Diagnostic {
  Say "Diagnostic de Mangadvisor"
  Ensure-Environment
  Check-Docker
  Wait-Postgres
  $health=Wait-Health
  Write-Host "API et PostgreSQL : OK ($($health.database))"
  $required=@("jikan_manga_source","manga","genre","manga_genre",
              "theme","manga_theme","demographic","manga_demographic",
              "manga_recommendation_edge","user_manga_library",
              "user_manga_inventory_declaration","manga_fr_edition")
  $counts=@{}
  foreach ($table in $required) {
    $counts[$table]=Get-Count $table
    Write-Host ("  {0,-36} {1,8}" -f $table,$counts[$table])
  }
  if ($counts["manga"] -eq 0) { throw "Catalogue vide : lance l'installation (1) ou actualise le catalogue (options avancees)." }
  if ($counts["manga_recommendation_edge"] -eq 0) {
    Write-Warning "Aucune recommandation communautaire : menu A puis option 2 (actualiser les recommandations)."
  }
  $url="http://127.0.0.1:$(Config 'API_PORT')/mangas?limit=1"
  $result=Invoke-RestMethod -Uri $url -TimeoutSec 15
  if ($null -eq $result) { throw "Recherche API vide/invalide." }
  $webUrl="http://127.0.0.1:$(Config 'UI_PORT')/"
  $web=Invoke-WebRequest -Uri $webUrl -UseBasicParsing -TimeoutSec 15
  if ([int]$web.StatusCode -ne 200) { throw "Interface web inaccessible : $webUrl" }
  # Validate the real browser network path, not merely static index.html.
  $proxyUrl="http://127.0.0.1:$(Config 'UI_PORT')/api/health"
  try {
    $proxy=Invoke-RestMethod -Uri $proxyUrl -TimeoutSec 15
    if ($proxy.status -ne "ok") { throw "Reponse inattendue du proxy." }
  } catch {
    throw "Le site est disponible, mais le proxy API ne fonctionne pas : $proxyUrl. Verifie les logs Docker web/api. Detail: $($_.Exception.Message)"
  }
  $libraryUrl="http://127.0.0.1:$(Config 'UI_PORT')/api/library?limit=1"
  try {
    $library=Invoke-RestMethod -Uri $libraryUrl -TimeoutSec 15
    if ($null -eq $library.items) { throw "JSON bibliotheque incomplet." }
  } catch {
    throw "La bibliotheque du site ne repond pas : $libraryUrl. Detail: $($_.Exception.Message)"
  }
  Write-Host "API directe, proxy Web et bibliotheque : OK ($webUrl)"
  Write-Host "Controle manuel restant : fiches, editions, recommandations et conseiller."
  Write-Host "Un diagnostic reussi ne garantit pas la pertinence des correspondances de la mangatheque."
}
function Backup {
  Say "Sauvegarde PostgreSQL et restauration de verification"
  $path=Join-Path $root "cmd\library-backup.ps1"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $path -Action Backup
  Assert-Exit "Echec de sauvegarde : aucune operation sensible ne doit continuer"
}
function Inventory {
  $path=Join-Path $root "private-data\mangatheque.csv"
  if (!(Test-Path -LiteralPath $path)) {
    Write-Host "CSV non trouve : $path"
    Write-Host "Copie ton fichier ici, puis menu A : tester (4) et importer (3)."
    return
  }
  Say "Inventaire personnel (apercu obligatoire)"
  $scriptFile=Join-Path $root "cmd\import-private-inventory.ps1"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptFile -PreviewOnly
  Assert-Exit "Echec de l'apercu de la mangatheque"
  if (Confirm "Executer maintenant l'import securise (confirmation supplementaire dans le script) ?" $false) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptFile
    Assert-Exit "Echec de l'import de la mangatheque"
  }
}
function Benchmark-Inventory {
  $csv=Join-Path $root "private-data\mangatheque.csv"
  if (!(Test-Path -LiteralPath $csv -PathType Leaf)) {
    Write-Host "Benchmark personnel ignore : pas de CSV local."
    return
  }
  Say "Benchmark de la mangatheque et du conseiller (lecture seule)"
  $scriptFile=Join-Path $root "cmd\benchmark-mangatheque.ps1"
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptFile -CsvFile $csv
  Assert-Exit "Benchmark personnel impossible. Menu A puis option 4 apres diagnostic"
}
function Update {
  Say "Mise a jour sans suppression des donnees"
  Ensure-Environment
  Check-Docker
  if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git absent : installe Git pour Windows (ou utilise une installation ZIP manuelle)."
  }
  if (!(Test-Path (Join-Path $root ".git"))) {
    throw "Ce dossier n'est pas un clone Git : impossible de faire git pull automatiquement."
  }
  $branchName=@(& git -C $root branch --show-current)
  Assert-Exit "Impossible de connaitre la branche Git active"
  if ($branchName.Count -ne 1 -or ([string]$branchName[0]).Trim() -cne "main") {
    throw "Mise a jour reservee a la branche main. Branche actuelle : $($branchName -join ', ')"
  }

  # A CRLF warning alone is harmless. Unlike 'git diff --quiet', porcelain
  # reports precisely which tracked files Git considers modified, including
  # staged changes. Ignored secrets and private data are never stashed.
  $trackedChanges=@(& git -C $root status --porcelain=v1 --untracked-files=no)
  Assert-Exit "Impossible de lire l'etat du depot Git"
  $needsStash=$trackedChanges.Count -gt 0
  if ($needsStash) {
    Say "Modifications locales detectees par Git"
    Write-Host ("Git signale {0} chemin(s) modifies. Les avertissements LF/CRLF ne suffisent pas a expliquer ces changements." -f $trackedChanges.Count)
    $trackedChanges | Select-Object -First 30 | ForEach-Object { Write-Host ("  " + $_) }
    if ($trackedChanges.Count -gt 30) { Write-Host "  ... autres fichiers modifies non affiches." }
    Write-Host "Ces modifications seront GARDEES dans une sauvegarde Git locale (stash)."
    Write-Host "Elles ne seront pas remises automatiquement dans le code mis a jour."
    Write-Host "Les fichiers ignores (.env, private-data, backups) et les volumes Docker ne sont pas inclus."
    if (!(Confirm "Sauvegarder ces modifications suivies dans Git puis poursuivre ?" $false)) {
      throw "Mise a jour annulee : aucun changement Git effectue."
    }
  }

  # Validate a consistent database backup BEFORE changing any tracked file.
  Backup
  $stashCreated=$false
  if ($needsStash) {
    $label="mangadvisor-avant-maj-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Run "git" @("-C",$root,"stash","push","-m",$label) "Impossible de sauvegarder les modifications locales"
    $remaining=@(& git -C $root status --porcelain=v1 --untracked-files=no)
    Assert-Exit "Impossible de confirmer la sauvegarde Git locale"
    if ($remaining.Count -gt 0) {
      throw "Certains fichiers suivis sont encore modifies apres stash : mise a jour annulee."
    }
    $stashCreated=$true
    Write-Host "Modifications locales sauvegardees sous le nom : $label"
    Write-Host "Pour les retrouver plus tard : git stash list"
  }
  try {
    Run "git" @("-C",$root,"pull","--ff-only","origin","main") "Git pull a echoue"
  } catch {
    if ($stashCreated) {
      Write-Warning "La sauvegarde Git stash est conservee. Ne supprime pas le depot."
      Write-Host "Voir la sauvegarde des modifications : git stash list"
    }
    throw
  }
  Initialize-Database
  Start-Application
  Diagnostic
  Write-Host "Mise a jour terminee. Fichiers personnels et volumes conserves."
}
function Wizard {
  Say "ASSISTANT COMPLET - Premiere installation ou reprise"
  Write-Host "Pre-requis : Docker Desktop installe, code telecharge (Git ou ZIP)."
  Write-Host "L'assistant ne lance JAMAIS Nuke, ne supprime PAS de volume."
  Write-Host "Le catalogue exige Internet pour joindre Tenrai. Les traitements sont relancables."
  if (!(Confirm "Demarrer l'installation guidee ?" $true)) { return }
  Ensure-Environment
  Initialize-Database
  Start-Application
  Load-Catalogue
  Load-Recommendations
  Diagnostic
  Backup
  Say "Import facultatif de ta mangatheque"
  $csv=Join-Path $root "private-data\mangatheque.csv"
  if (!(Test-Path -LiteralPath $csv)) {
    Write-Host "Copie maintenant ta collection CSV dans : $csv"
    $null=Read-Host "Appuie sur Entree quand la copie est faite (ou pour ignorer)"
  }
  Inventory
  # Protect any newly imported ownership claims before diagnostic/quality calls.
  Backup
  Diagnostic
  # The audit never writes SQL and its report stays under private-data.
  # An unavailable benchmark must not undo or invalidate a safe installation.
  try {
    Benchmark-Inventory
  } catch {
    Write-Warning ("Benchmark facultatif non abouti : " + $_.Exception.Message)
    Write-Host "Relance le benchmark via le menu A, option 4."
  }
  Say "Fin de l'assistant"
  Write-Host ("Ouvre http://localhost:" + (Config "UI_PORT"))
  Write-Host "Mobile HTTPS et IA locale : menu A (options avancees)."
  Write-Host "Sauvegarde finale terminee et verifiee. Copie les fichiers du dossier backups sur un deuxieme support."
}
try {
  switch ($Action) {
    "Environment"     { Ensure-Environment }
    "Start"           { Open-Application }
    "Stop"            { Stop-Application }
    "Database"        { Initialize-Database }
    "Catalogue"       { Load-Catalogue }
    "Recommendations" { Load-Recommendations }
    "Network"         { Network }
    "Diagnostic"      { Diagnostic }
    "Update"          { Update }
    "Wizard"          { Wizard }
  }
  Write-Host ""
  Write-Host "Operation terminee."
} catch {
  Write-Host ""
  Write-Host ("ERREUR : " + $_.Exception.Message) -ForegroundColor Red
  Write-Host "Aucune suppression automatique des volumes n'a ete lancee."
  exit 1
}
