# Read-only overview of the public source graph. Never rebuilds data.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
Assert-MangadvisorStableCheckout $root
$container="mangadvisor_api"
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker introuvable. Lance Mangadvisor avant d'afficher le bilan."
}
$raw=@(& docker container inspect --format '{{json .Config.Labels}}' $container)
if ($LASTEXITCODE -ne 0 -or $raw.Count -ne 1) {
    throw "API absente. Lance Mangadvisor avec l'option 2."
}
$labels=ConvertFrom-Json ([string]$raw[0])
if ($labels.'com.docker.compose.project' -cne "mangadvisor" -or
    $labels.'com.docker.compose.service' -cne "api") {
    throw "Le conteneur ne correspond pas a l'API Mangadvisor."
}
Write-Host "Etat du referentiel bibliographique public (lecture seule)" -ForegroundColor Cyan
& docker exec -i $container python -m apps.api.app.catalogue_source_graph_cli --report-only
if ($LASTEXITCODE -ne 0) {
    throw "Lecture du bilan impossible. Aucune base modifiee."
}
