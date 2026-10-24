# Mangadvisor - single WEB deployment, stable default Compose stack.
# Requires PowerShell 5.1+, Docker Desktop; no Python installation on Windows.
# All database/catalog/recommendation jobs run in Docker; secrets stay in .env.
param(
  [ValidateSet("Environment","Database","Catalogue","CatalogueExtended","Recommendations","Network","Diagnostic","Update","Wizard","Start","Stop","Status","Logs","Inventory","BnF","BnFBulk","SourcesBenchmark","SourcesBenchmarkV2","BibliographicStaging","CompleteMALCatalogue","CatalogueFrenchScrinis","BibliographyPilot","CatalogueLifecycle","Wikidata","LibraryEnrichment","SearchIndex","Aliases")]
  [string]$Action="Wizard"
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
Assert-MangadvisorStableCheckout $root
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
    # Creating fresh credentials is safe ONLY for a brand-new installation.
    # An existing persistent PostgreSQL volume could still contain the
    # user's complete inventory, even when all containers are stopped.
    $dockerAvailable=$null -ne (Get-Command docker -ErrorAction SilentlyContinue)
    if ($dockerAvailable) {
      & docker info --format "{{.ServerVersion}}" 1>$null 2>$null
      $dockerAvailable=$LASTEXITCODE -eq 0
    }
    if ($dockerAvailable) {
      # Enumerate rather than inspect a non-existent object: under Windows
      # PowerShell 5.1 stderr may terminate even with 2>$null.
      $names=@(& docker container ls -a --format "{{.Names}}")
      Assert-Exit "Lecture des conteneurs Docker impossible"
      if ($names -contains "mangadvisor_postgres") {
        throw "Ancien PostgreSQL Mangadvisor detecte sans .env. Recuperer l'ancienne configuration avant toute mise a jour."
      }
      $volumes=@(& docker volume ls --format "{{.Name}}")
      Assert-Exit "Lecture des volumes Docker impossible"
      foreach ($volume in @("mangadvisor_mangadvisor_pgdata",
                             "mangadvisor_mangadvisor_meili")) {
        if ($volumes -contains $volume) {
          throw "Volume Docker $volume present sans .env : installation ancienne detectee. Recuperer la configuration d'origine."
        }
      }
    } else {
      # Still permit generating offline install settings (Windows setup/CI).
      # Their compatibility with any old Docker volumes MUST be checked by
      # library-backup.ps1 before the first update or database backup.
      Write-Warning "Docker indisponible : nouvelle configuration non validee contre d'eventuels volumes existants."
    }
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
function Remove-Legacy-Ui {
  # A container name is not proof of ownership. Never remove a foreign container.
  $oldUi=@(& docker container ls -a --format "{{.Names}}" |
    Where-Object { $_ -ceq "mangadvisor_ui" })
  Assert-Exit "Liste des conteneurs Docker indisponible"
  if ($oldUi.Count -eq 0) { return }
  $raw=@(& docker container inspect --format '{{json .Config.Labels}}' mangadvisor_ui)
  Assert-Exit "Inspection de l'ancien conteneur UI impossible"
  if ($raw.Count -ne 1) { throw "Etiquettes de l'ancien conteneur UI absentes." }
  try {
    $labels=ConvertFrom-Json -InputObject ([string]$raw[0]) -ErrorAction Stop
  } catch {
    throw "Etiquettes de l'ancien conteneur UI invalides. Suppression annulee."
  }
  if ($null -eq $labels) { throw "Ancien conteneur UI sans proprietaire Compose." }
  $project=$labels.PSObject.Properties['com.docker.compose.project']
  $service=$labels.PSObject.Properties['com.docker.compose.service']
  if ($null -eq $project -or ([string]$project.Value) -cne "mangadvisor" -or
      $null -eq $service -or ([string]$service.Value) -cne "ui") {
    throw "Le conteneur mangadvisor_ui ne correspond pas au service historique Mangadvisor. Suppression refusee."
  }
  # Only the verified obsolete UI container is deleted; volumes stay untouched.
  Run "docker" @("rm","-f","mangadvisor_ui") "Impossible de retirer l'ancien conteneur UI"
}
function Start-Application([bool]$Build=$true) {
  Say "Demarrage des services Mangadvisor"
  Ensure-Environment
  Check-Docker
  Remove-Legacy-Ui
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
  # The optional automation profile must be stopped explicitly.
  # Leaving it running would keep writing PostgreSQL while the app is off.
  $state=@(& docker inspect --format "{{.State.Running}}" mangadvisor_catalog_sync 2>$null)
  if ($LASTEXITCODE -eq 0 -and $state.Count -gt 0 -and
      ([string]$state[0]).Trim() -eq "true") {
    Compose @("--profile","automation","stop","catalog-sync")
    Write-Host "Veille quotidienne arretee avant les autres services."
  }
  Compose @("stop")
  Write-Host "Services et veille arretes. Volumes PostgreSQL et fichiers prives conserves."
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
function Show-Service-Status {
  Say "Etat des conteneurs Mangadvisor"
  Ensure-Environment
  Check-Docker
  Compose @("--profile","automation","ps","--all")
}
function Show-Docker-Logs {
  Say "Journaux Docker Mangadvisor (CTRL+C pour quitter)"
  Ensure-Environment
  Check-Docker
  Compose @("--profile","automation","logs","--tail","120","-f")
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
  $pages=Ask-Number "Nombre de pages SEARCH Tenrai (25 mangas/page)" 40 2000
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
  try { Reindex-Manga-Search } catch {
    Write-Warning ("Recherche SQL disponible ; index Meilisearch non actualise : " + $_.Exception.Message)
  }
}
function Enrich-Catalogue-French-Scrinis {
  Say "Enrichir le catalogue MAL existant avec Scrinis FR (titres visibles)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $total=Get-Count "manga"
  Write-Host ("Catalogue MAL existant : {0} oeuvres" -f $total)
  Write-Host "Cette etape travaille SUR les oeuvres deja presentes dans PostgreSQL."
  Write-Host "Elle interroge Scrinis par titre public, verifie les auteurs/identifiants."
  Write-Host "Un titre francais n'est enregistre que si une publication FR papier avec ISBN est confirmee."
  Write-Host "Les doublons, homonymes, derivations et auteurs contradictoires restent non lies."
  Write-Host "AUCUNE mangatheque, edition ISBN, numero de tome ou progression n'est modifiee."
  $limit=Ask-Number "Combien d'oeuvres MAL traiter dans ce lot (max 100) ?" 20 100
  Write-Host "Une requete Scrinis attend environ 4,5 secondes entre appels (quota respecte)."
  if (!(Confirm "Enrichir ces fiches du catalogue en preservant toutes les editions personnelles ?" $false)) {
    Write-Host "Aucune modification."
    return
  }
  Backup
  Engine @("pipelines/engine/scripts/enrich_catalogue_scrinis_fr.py","--limit",[string]$limit)
  Write-Host "Nouveaux titres FR et auteurs consultables directement dans Mangadvisor."
  Write-Host "Pour les statistiques reelles : /catalogue/coverage sur ton API."
}
function Manage-Catalogue-Lifecycle {
  Say "Catalogue vivant : base MAL complete + mises a jour automatiques"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  Write-Host "Le catalogue MAL/Jikan initial est charge une seule fois via A -> 19."
  Write-Host "Chaque cycle quotidien : nouvelles oeuvres MAL + fiches anciennes tournantes."
  Write-Host "Enrichissements limites : Scrinis, MangaUpdates, BnF SRU et fichiers mensuels deja presents."
  Write-Host "Jamais de retour aux 858 pages a chaque demarrage."
  Write-Host "Ne modifie JAMAIS tes livres possedes, editions declarees, notes ou lectures."
  Write-Host "L'automatisme ne fonctionne que lorsque Docker Desktop tourne sur ce PC."
  Write-Host "1 - Verifier le catalogue initial (aucun appel Internet)"
  Write-Host "2 - Executer un cycle MAINTENANT (nouveautes uniquement)"
  Write-Host "3 - ACTIVER la synchronisation quotidienne Docker"
  Write-Host "4 - ARRETER la synchronisation quotidienne Docker"
  Write-Host "5 - Dernier rapport de veille et etat du service"
  $choice=(Read-Host "Ton choix (1-5)").Trim()
  switch ($choice) {
    "1" {
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--audit")
    }
    "2" {
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--audit")
      if (!(Confirm "Sauvegarder puis mettre a jour les seules nouvelles fiches MAL et candidates ?" $false)) { return }
      Backup
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--once")
    }
    "3" {
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--audit")
      if (!(Confirm "ACTIVER la veille quotidienne pendant que Docker Desktop fonctionne ?" $false)) { return }
      Backup
      Compose @("--profile","automation","up","-d","--build","catalog-sync")
      Write-Host "Veille auto ACTIVE dans le conteneur mangadvisor_catalog_sync."
      Write-Host "Premier cycle au demarrage puis un cycle par jour tant que Docker fonctionne."
      Write-Host "Pour afficher le journal :"
      Compose @("--profile","automation","logs","--tail","40","catalog-sync")
    }
    "4" {
      if (!(Confirm "Desactiver la veille automatique du catalogue ?" $false)) { return }
      Compose @("--profile","automation","stop","catalog-sync")
      Compose @("--profile","automation","rm","-f","catalog-sync")
      Write-Host "Veille desactivee sans suppression de PostgreSQL, JSON ou mangatheque."
    }
    "5" {
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--status")
      Compose @("--profile","automation","ps","catalog-sync")
      Write-Host "Fichier de controle : data\logs\catalogue_lifecycle\last_cycle.json"
    }
    default { Write-Host "Action annulee. Choisir une valeur de 1 a 5." }
  }
}

function Load-Complete-MAL-Catalogue {
  param([switch]$InitialSetup)
  Say "Catalogue MAL/Jikan complet via Tenrai : base du projet"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  $before=Get-Count "manga"
  Write-Host "L'API publique Jikan est fermee depuis le 01/10/2026."
  Write-Host "Tenrai donne acces au catalogue public MyAnimeList au format compatible Jikan."
  Write-Host "Parcours : toutes categories manga, tri MAL ID ascendant, sans filtre SFW, 100 notices/page."
  Write-Host "La source annonce sa vraie derniere page ; 20000 est seulement un garde-fou."
  Write-Host "Le rapport montrera si toutes les pages et references ont ete recuperees."
  $jikanDirectory=Join-Path $root "data\raw\jikan"
  Write-Host ("Repertoire Jikan historique sur Windows : " + $jikanDirectory)
  Write-Host "Les fichiers du catalogue complet : manga_page_1.json, manga_page_2.json, etc."
  Write-Host "Migration des pages deja recuperees depuis l'ancien sous-dossier : AUCUN appel API, AUCUNE ecriture SQL."
  Engine @("pipelines/engine/scripts/sync_full_mal_catalogue.py","--repair-layout")
  Write-Host "Derniere synchronisation et emplacement des vrais JSON :"
  Engine @("pipelines/engine/scripts/sync_full_mal_catalogue.py","--status")
  Write-Host "Si la derniere synchronisation est complete, tu as deja les donnees : pas besoin de les telecharger."
  if ($InitialSetup) {
    # A new installation MUST not stop after a filtered sample catalogue.
    # Reuse an audited complete local base rather than download it again.
    $complete=$false
    try {
      Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--audit")
      $complete=$true
    } catch {
      Write-Host "Aucune base MAL complete et auditee : premier chargement requis."
    }
    if ($complete) {
      Write-Host "Catalogue MAL complet deja valide : aucune reinitialisation."
      try { Reindex-Manga-Search } catch {
        Write-Warning ("Recherche SQL disponible ; index Meilisearch non actualise : " + $_.Exception.Message)
      }
      return
    }
    if (!(Confirm "Installer le catalogue public MAL complet (premiere installation) ?" $true)) {
      throw "Installation incomplete : socle MAL absent. L'application ne sera pas declaree prete."
    }
  } else {
    if (!(Confirm "Faire une NOUVELLE synchronisation du catalogue public MAL ?" $false)) {
      Write-Host ("Fichiers existants conserves dans " + $jikanDirectory)
      Write-Host "La base PostgreSQL et la mangatheque n'ont pas ete modifiees."
      return
    }
  }
  Network
  Engine @("pipelines/engine/scripts/sync_full_mal_catalogue.py","--plan")
  if (!(Confirm "Confirmer les appels API et la consolidation des notices ?" $InitialSetup)) {
    if ($InitialSetup) { throw "Installation incomplete : chargement MAL non confirme." }
    Write-Host "La migration des fichiers existants est terminee ; pas de nouvelle synchronisation."
    return
  }
  $refresh=Confirm "Retelcharger toutes les pages, y compris celles du cache valide ?" $false
  Backup
  $params=@("pipelines/engine/scripts/sync_full_mal_catalogue.py",
            "--batch-pages","20","--pause","1.1")
  if ($refresh) { $params+=@("--refresh") }
  Engine $params
  # Never consolidate an incomplete source pass. Engine above must succeed.
  foreach ($sql in @(
    "sql\schema\003_build_canonical_from_jikan.sql",
    "sql\schema\004_add_theme_demographic_tables.sql",
    "sql\schema\005_build_theme_demographic_from_jikan.sql")) {
    Sql-File $sql
  }
  Engine @("pipelines/engine/scripts/sync_full_mal_catalogue.py","--finalize")
  if ($InitialSetup) {
    Engine @("pipelines/engine/scripts/catalogue_lifecycle.py","--audit")
  }
  $after=Get-Count "manga"
  $source=Get-Count "jikan_manga_source"
  Write-Host ("Mangas canonises avant : {0} ; apres : {1} ; progression nette : {2}" -f
              $before,$after,($after-$before))
  Write-Host ("Notices source MAL distinctes : {0}" -f $source)
  Write-Host ("Pages brutes Jikan : " + $jikanDirectory)
  Write-Host "Rapport de suivi : data\logs\catalogue_complete\last_sync.json"
  Write-Host "Fiches de ta mangatheque et relations existantes conservees."
  try { Reindex-Manga-Search } catch {
    Write-Warning ("Recherche SQL disponible ; index Meilisearch non actualise : " + $_.Exception.Message)
  }
}
function Load-Extended-Catalogue {
  Say "Catalogue Tenrai etendu : progression jusqu'a la derniere page"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  $before=Get-Count "manga"
  Network
  $maxPages=Ask-Number "Plafond de pages Manga (25 notices par page, max 2000)" 600 2000
  $withOneShots=Confirm "Inclure aussi la categorie One-shot ?" $true
  $force=Confirm "Rafraichir les pages Tenrai deja en cache ?" $false
  Write-Host "Extraction progressive. L'arret intervient a la derniere page ou au plafond."
  Write-Host "Les pages telechargees restent sur disque en cas de coupure ; la reprise les reutilise."
  Backup
  $base=@("--mode","search","--start-page","1","--limit","25",
          "--sleep-seconds","1","--until-end","--no-legacy-search-copy",
          "--sfw","true","--order-by","popularity","--sort","asc")
  $mangaArgs=@("pipelines/engine/scripts/extract_jikan.py")+
              $base+@("--manga-type","manga","--end-page",[string]$maxPages)
  if ($force) { $mangaArgs+=@("--force") }
  Engine $mangaArgs
  if ($withOneShots) {
    $oneShotMax=[Math]::Min($maxPages,200)
    $oneShotArgs=@("pipelines/engine/scripts/extract_jikan.py")+
                  $base+@("--manga-type","oneshot","--end-page",[string]$oneShotMax)
    if ($force) { $oneShotArgs+=@("--force") }
    Engine $oneShotArgs
  }
  Engine @("pipelines/engine/scripts/load_jikan_to_postgres.py","--sources","search","top")
  foreach ($sql in @(
    "sql\schema\003_build_canonical_from_jikan.sql",
    "sql\schema\004_add_theme_demographic_tables.sql",
    "sql\schema\005_build_theme_demographic_from_jikan.sql")) {
    Sql-File $sql
  }
  $after=Get-Count "manga"
  $sourceCount=Get-Count "jikan_manga_source"
  if ($after -eq 0) { throw "Catalogue vide apres extraction : verifier les journaux." }
  Write-Host ("Catalogue avant : {0} / apres : {1} / variation nette : {2}" -f $before,$after,($after-$before))
  Write-Host ("Notices distinctes en provenance fournisseur : {0}" -f $sourceCount)
  Write-Host "Operation non destructive. Les alias FR et les ISBN sont traites separement."
}
function Prepare-Bibliographic-Staging {
  Say "Preparation bibliographique : Scrinis, MangaUpdates, BnF (staging uniquement)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  $null=Get-Count "manga"
  Write-Host "Source : dernier rapport JSON V2 local, genere via A -> 17."
  Write-Host "Aucune interrogation Internet n'est effectuee dans cette etape."
  Write-Host "Preparation sans ecriture PostgreSQL :"
  Engine @("pipelines/engine/scripts/prepare_bibliographic_staging.py","--preview")
  Write-Host "Les candidats d'oeuvres et editions restent a valider."
  Write-Host "Les ISBN BnF restent des indices bibliographiques, pas des tomes possedes."
  Write-Host "Les operations SQL sont limitees aux 4 tables bib_stage_* ; pas de fusion."
  if (!(Confirm "Enregistrer ce lot dans la zone de preparation bibliographique SQL ?" $false)) {
    Write-Host "Aucun changement en base. Les fichiers d'apercu restent locaux."
    return
  }
  Engine @("pipelines/engine/scripts/prepare_bibliographic_staging.py","--import")
  Write-Host "Lots de preparation enregistres :"
  Engine @("pipelines/engine/scripts/prepare_bibliographic_staging.py","--status")
  Write-Host ("Fichiers d'apercu : " + (Join-Path $root "data\logs\bibliographic_staging"))
  Write-Host "Aucune entree du catalogue ou de la mangatheque n'a ete modifiee."
}
function Benchmark-Catalogue-Sources-V2 {
  Say "Comparatif V2 : mangas FR papier, scores oeuvre/edition et candidats concurrents"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $null=Wait-Health
  $null=Get-Count "manga"
  $count=Ask-Number "Nombre de mangas a comparer (max 50)" 50 50
  $details=Ask-Number "Maximum de fiches detaillees PAR API (max 20)" 12 20
  Write-Host "Mangatheque : cible par defaut FR / papier (hypothese, pas preuve de possession)."
  Write-Host "Catalogue general : edition internationale non restreinte."
  Write-Host "Les editions declarees sur ce PC servent au classement LOCAL et ne sont pas envoyees aux API."
  Write-Host "Apercu des titres sans acces Internet :"
  Engine @("pipelines/engine/scripts/benchmark_manga_sources_v2.py",
           "--limit",[string]$count,"--detail-limit",[string]$details,"--dry-run")
  Write-Host "Recherches API par titres uniquement ; certaines fiches detaillees seront lues."
  Write-Host "Quotas stricts : Scrinis 15 appels/min sans cle ; MangaUpdates pause 2 secondes."
  Write-Host "Les resultats restent dans data\logs\catalog_sources ; aucun changement SQL."
  Write-Host "Deux indicateurs distincts : correspondance oeuvre et edition FR papier (preuves, pas probabilites)."
  Write-Host "Les ISBN eventuels ne prouvent ni la possession ni l'edition declaree."
  if (!(Confirm "Autoriser les recherches publiques du benchmark V2 ?" $false)) {
    Write-Host "Operation annulee. Aucun appel distant n'a ete effectue."
    return
  }
  Engine @("pipelines/engine/scripts/benchmark_manga_sources_v2.py",
           "--limit",[string]$count,"--detail-limit",[string]$details)
  Write-Host ("Rapports CSV et JSON V2 : " + (Join-Path $root "data\logs\catalog_sources"))
}
function Import-BnF-Bulk {
  Say "Importer des lots bibliographiques officiels BnF (zone de candidats)"
  Ensure-Environment
  Check-Docker
  $dir=Join-Path $root "data\raw\bnf\imports"
  if (!(Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
  }
  Write-Host "Source officielle : https://api.bnf.fr/index.php/fr/produits_bibliographiques_mensuels"
  Write-Host "Telecharge uniquement les LIVRES au format UNIMARC UTF8 (ISO 2709)."
  Write-Host "Depose les archives ou fichiers .not/.mrc/.iso/.marc/.gz/.zip dans : $dir"
  $files=@(Get-ChildItem -LiteralPath $dir -File | Where-Object {
    $_.Name -match '\.(not|mrc|iso|marc|gz|zip)$'
  })
  if ($files.Count -eq 0) {
    Write-Host "Aucun fichier BnF local. Aucun traitement lance."
    return
  }
  Write-Host ("Fichiers detectes : " + $files.Count)
  if ($files.Count -gt 20) {
    throw "Plus de 20 fichiers BnF ; traiter des lots plus petits pour une reprise sure."
  }
  Compose @("up","-d","postgres","meilisearch")
  Wait-Postgres
  Say "Apercu sans modification"
  Engine @("pipelines/engine/scripts/bnf_bulk_import.py","--preview")
  Write-Host "Les notices retenues restent des candidates independantes."
  Write-Host "Aucun ISBN ne sera rattache automatiquement a une oeuvre ou a ta collection."
  if (!(Confirm "Sauvegarder puis importer le lot dans la zone BnF ?" $false)) {
    Write-Host "Import annule. Les fichiers et donnees existants sont conserves."
    return
  }
  Backup
  Engine @("pipelines/engine/scripts/bnf_bulk_import.py")
  Write-Host "Notices BnF candidates importees ; edition et tome non confirmes."
}
function Run-Bibliography-Pilot {
  Say "Pilote bibliographique BnF et Scrinis - candidats uniquement"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  Write-Host "Lot borne a 10 mangas. Recherche BnF 3 pages par titre."
  Write-Host "Les ISBN croises BnF/Scrinis ne sont PAS des editions confirmees."
  Write-Host "Seules les notices candidates BnF et alias FR verifies Scrinis sont enregistres."
  Write-Host "La mangatheque, les volumes declares et les editions confirmees restent intacts."
  $limit=Ask-Number "Combien de mangas traiter (maximum 10) ?" 5 10
  if (!(Confirm "Lancer ce pilote avec une sauvegarde prealable ?" $false)) {
    Write-Host "Aucun traitement lance."
    return
  }
  Backup
  Engine @("-m","pipelines.engine.scripts.bibliography_pipeline","--limit",[string]$limit)
}

function Enrich-BnF {
  Say "Enrichissement progressif depuis le catalogue BnF"
  Ensure-Environment
  Check-Docker
  # Ensure the API startup creates the additive, candidate-only staging tables.
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $limit=Ask-Number "Nombre de mangas a rechercher dans la BnF (max 25)" 10 25
  $refresh=Confirm "Relancer aussi des recherches deja faites recemment ?" $false
  Write-Host "Les resultats BnF seront des CANDIDATS, jamais des editions confirmees."
  Write-Host "Aucune association de manga, ISBN ou tome n'est effectuee automatiquement."
  # Consistent verified recovery point before any staged metadata write.
  Backup
  $argsList=@("run","--rm","--no-deps","api","python","-m",
              "apps.api.app.bnf_batch","--limit",[string]$limit)
  if ($refresh) { $argsList+=@("--refresh") }
  Compose $argsList
  Write-Host "Recherche terminee : ouvre une fiche manga pour voir les candidats BnF."
}
function Enrich-Wikidata {
  Say "Enrichissement Wikidata des mangas (libelles FR et genres documentes)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $limit=Ask-Number "Nombre de mangas a interroger via Wikidata (max 15)" 8 15
  $refresh=Confirm "Actualiser les informations deja interrogees ?" $false
  Write-Host "Source CC0 Wikidata : association uniquement par identifiant MAL manga P4087."
  Write-Host "Une etiquette en francais ne certifie pas une edition francaise."
  Backup
  $argsList=@("run","--rm","--no-deps","api","python","-m",
              "apps.api.app.wikidata_enrichment","--limit",[string]$limit)
  if ($refresh) { $argsList+=@("--refresh") }
  Compose $argsList
  Write-Host "Enrichissement Wikidata termine. Consulte les fiches mangas."
}
function Enrich-Multilingual-Aliases {
  Say "Titres alternatifs fiables FR / EN / JA (Wikidata)"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $limit=Ask-Number "Nombre de mangas Wikidata deja lies a enrichir (max 20)" 12 20
  $refresh=Confirm "Reprendre meme les mangas deja enrichis recemment ?" $false
  Write-Host "Les alias sont relies aux manga par MAL ID P4087, reverifie cote Wikidata."
  Write-Host "Aucune edition francaise ou possession ne sera attribuee automatiquement."
  Backup
  $argsList=@("run","--rm","--no-deps","api","python","-m",
              "apps.api.app.multilingual_aliases","--limit",[string]$limit)
  if ($refresh) { $argsList+=@("--refresh") }
  Compose $argsList
  Write-Host "Recherche catalogue / inventaire actualisee via les titres alternatifs verifies."
}
function Enrich-My-Library {
  Say "Enrichir toute ma mangatheque reconnue depuis Wikidata et la BnF"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  Wait-Postgres
  $maxWorks=Ask-Number "Maximum de series de ma mangatheque liees au catalogue (max 250)" 80 250
  $useBnf=Confirm "Rechercher aussi les notices BnF (plus lent, ISBN a verifier) ?" $true
  $bnfLabel=if ($useBnf) { "OUI" } else { "NON" }
  Write-Host "Sources selectionnees : Wikidata = OUI ; BnF = $bnfLabel"
  Write-Host "Une seule sauvegarde verifiee est creee avant les recherches."
  Write-Host "Les lignes d'inventaire sans manga identifie resteront en attente."
  Write-Host "Aucune edition, aucun tome et aucun ISBN ne sont attribues automatiquement."
  Backup
  $argsList=@("run","--rm","--no-deps","api","python","-m",
              "apps.api.app.library_enrichment","--max-works",[string]$maxWorks)
  if (-not $useBnf) { $argsList+=@("--skip-bnf") }
  Compose $argsList
  Write-Host "Bilan ci-dessus : consulte les fiches mangas et les candidats ISBN."
}
function Reindex-Manga-Search {
  Say "Index de recherche multilingue Meilisearch"
  Ensure-Environment
  Check-Docker
  Compose @("up","-d","postgres","meilisearch","api")
  $null=Wait-Health
  Write-Host "Index public : titres FR/EN/JA, alias verifies, genres. Aucune donnee personnelle."
  Write-Host "PostgreSQL reste la source unique ; construction d'un index temporaire puis permutation."
  Compose @("exec","-T","api","python","-m","apps.api.app.search_index")
  Write-Host "Index Meilisearch actualise. En cas de panne, la recherche SQL reste disponible."
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
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Script de sauvegarde absent. Utilise le menu 7 pour recuperer les fichiers depuis GitHub."
  }
  # Update cannot cure a broken old backup script because backup runs first.
  # Recognize old code BEFORE docker exec or any database operation.
  $source=[IO.File]::ReadAllText($path,[Text.Encoding]::UTF8)
  if (-not $source.Contains("function Prepare-Existing-Postgres")) {
    $rev=@(& git -C $root rev-parse --short HEAD 2>$null)
    throw "Script de sauvegarde obsolete (version Git : $($rev -join '')). Choisir 7 pour synchroniser le CODE ; si le probleme persiste, comparer git log -1 et git status -sb. Aucun volume touche."
  }
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
    # Every user-initiated import must have a verified recovery point.
    # The preview above never writes to PostgreSQL; no backup is required
    # unless the user explicitly chooses the write path.
    Backup
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
    # The shared Git synchronizer detects untracked files which now exist
    # upstream and archives ONLY those conflicts outside this repository.
    # Tracked edits have already been backed up into Git stash above.
    $syncScript=Join-Path $root "cmd\github-sync.ps1"
    if (!(Test-Path -LiteralPath $syncScript -PathType Leaf)) {
      throw "Synchronisation GitHub indisponible : cmd\github-sync.ps1 manque."
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $syncScript -Root $root -NonInteractive
    Assert-Exit "La synchronisation GitHub a echoue"
  } catch {
    if ($stashCreated) {
      Write-Warning "La sauvegarde Git stash est conservee. Ne supprime pas le depot."
      Write-Host "Voir la sauvegarde des modifications : git stash list"
    }
    throw
  }
  Initialize-Database
  Start-Application
  Write-Host "Apres une mise a jour du catalogue, relancer la recherche intelligente via A -> 22."
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
  # The Web API initializes optional application schemas needed by the
  # backup verifier; the catalogue is then fully loaded, NOT the old
  # 40-page popularity/SFW sample.
  Start-Application
  Load-Complete-MAL-Catalogue -InitialSetup
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
    "Status"          { Show-Service-Status }
    "Logs"            { Show-Docker-Logs }
    "Database"        { Initialize-Database }
    "Inventory"       { Inventory }
    "BnF"             { Enrich-BnF }
    "BnFBulk"         { Import-BnF-Bulk }
    "SourcesBenchmark" { Benchmark-Catalogue-Sources-V2 }
    "SourcesBenchmarkV2" { Benchmark-Catalogue-Sources-V2 }
    "BibliographicStaging" { Prepare-Bibliographic-Staging }
    "Wikidata"        { Enrich-Wikidata }
    "LibraryEnrichment" { Enrich-My-Library }
    "Aliases"         { Enrich-Multilingual-Aliases }
    "Catalogue"       { Load-Catalogue }
    "CatalogueExtended" { Load-Extended-Catalogue }
    "CompleteMALCatalogue" { Load-Complete-MAL-Catalogue }
    "CatalogueFrenchScrinis" { Enrich-Catalogue-French-Scrinis }
    "BibliographyPilot" { Run-Bibliography-Pilot }
    "CatalogueLifecycle" { Manage-Catalogue-Lifecycle }
    "Recommendations" { Load-Recommendations }
    "SearchIndex"     { Reindex-Manga-Search }
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
