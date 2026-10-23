# AniList public catalogue batch. No owner inventory or editions.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
Assert-MangadvisorStableCheckout $root
$container="mangadvisor_api"
$labels=@(& docker container inspect --format '{{json .Config.Labels}}' $container)
if ($LASTEXITCODE -ne 0 -or $labels.Count -ne 1) {
    throw "Demarre Mangadvisor (option 2) avant ce traitement."
}
$meta=ConvertFrom-Json ([string]$labels[0])
if ($meta.'com.docker.compose.project' -cne "mangadvisor" -or $meta.'com.docker.compose.service' -cne "api") {
    throw "Conteneur Mangadvisor API attendu."
}
Write-Host "Enrichissement catalogue public depuis AniList, 64 mangas par lot..."
& docker exec -i $container python -m apps.api.app.catalogue_anilist_batch --run --limit 64
if ($LASTEXITCODE -ne 0) {
    throw "Source indisponible ou execution interrompue. Lots deja valides conserves."
}
Write-Host "Lot termine, relance possible sans duplications."
