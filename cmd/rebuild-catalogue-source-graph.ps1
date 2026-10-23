# Reconstruct a PUBLIC-only work graph from the EXISTING 85k catalogue.
# Existing manga, Jikan JSON and personal collection remain unchanged.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
Assert-MangadvisorStableCheckout $root
$container="mangadvisor_api"
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker est introuvable."
}
$labels=@(& docker container inspect --format '{{json .Config.Labels}}' $container)
if ($LASTEXITCODE -ne 0 -or $labels.Count -ne 1) {
    throw "Lance d'abord Mangadvisor (option 2). L'API doit etre active."
}
$meta=ConvertFrom-Json ([string]$labels[0])
if ($meta.'com.docker.compose.project' -cne "mangadvisor" -or
    $meta.'com.docker.compose.service' -cne "api") {
    throw "Conteneur incorrect. Aucun changement effectue."
}
Write-Host "Creation du referentiel public des oeuvres et des preuves..." -ForegroundColor Cyan
Write-Host "Les donnees Jikan, les ISBN possedes et ta mangatheque restent inchanges."
Write-Host "Aucun appel Internet n'est lance par cette etape."
# Production API image intentionally contains apps/api, NOT pipelines/engine.
# Use the API-owned CLI rather than the engine-only module.
& docker exec -i $container python -m apps.api.app.catalogue_source_graph_cli --apply
if ($LASTEXITCODE -ne 0) {
    throw "Echec de reconstruction. Aucun effacement des donnees d'origine."
}
Write-Host ""
Write-Host "Referentiel reconstruit. Consulte le bilan JSON ci-dessus." -ForegroundColor Green
