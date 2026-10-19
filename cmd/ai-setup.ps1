# Mangadvisor optional LOCAL AI installation for Windows / Docker Desktop.
# No cloud key or paid service. Model download only after explicit menu choice 15.
param([switch]$Stop)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $root ".env"
$compose = @("-f",(Join-Path $root "infra\compose\docker-compose.yml"),
             "-f",(Join-Path $root "infra\compose\docker-compose.local.yml"))
$model = "qwen2.5:3b"
function Assert-LastExit([string]$message) {
  if ($LASTEXITCODE -ne 0) { throw "$message (code $LASTEXITCODE)." }
}
function Set-Config([string]$key,[string]$value) {
  # Preserve all unknown and user-configured .env entries.
  $lines = [System.Collections.Generic.List[string]]::new()
  foreach ($line in [System.IO.File]::ReadAllLines($envFile)) {
    if ($line -notmatch ('^\s*'+[regex]::Escape($key)+'\s*=')) { $lines.Add($line) }
  }
  $lines.Add("$key=$value")
  [System.IO.File]::WriteAllLines($envFile,$lines,[System.Text.UTF8Encoding]::new($false))
}
if (!(Test-Path $envFile)) {
  throw "Fichier .env introuvable : installe et configure Mangadvisor avant de lancer l'IA."
}
docker info --format "{{.ServerVersion}}" 1>$null 2>$null
Assert-LastExit "Docker Desktop doit etre demarre."
Push-Location $root
try {
  if ($Stop) {
    Set-Config "OLLAMA_ENABLED" "false"
    & docker compose --env-file $envFile @compose stop ollama
    # Stopping a service not yet created may fail: no personal data is removed.
    & docker compose --env-file $envFile @compose up -d api
    Assert-LastExit "Impossible de reactiver le conseiller guide."
    Write-Host "IA locale arretee. Conseiller guide actif. Modele conserve sur disque."
    exit 0
  }

  Write-Host ""
  Write-Host "Configuration du conseiller IA LOCAL (modele : $model)."
  Write-Host "Ce modele prend plusieurs Go sur le disque et demande de la RAM."
  Write-Host "Premier lancement : telechargement du modele depuis Ollama."
  Write-Host "Aucun abonnement a une API distante n'est necessaire."
  Write-Host ""
  $answer=Read-Host "Activer et telecharger le modele maintenant ? (O/N)"
  if ($answer -notmatch '^(o|oui|y|yes)$') {
    Write-Host "Annule : Mangadvisor reste en mode guide."
    exit 0
  }

  & docker compose --env-file $envFile @compose --profile ai up -d ollama
  Assert-LastExit "Impossible de demarrer Ollama."
  & docker exec mangadvisor_ollama ollama pull $model
  Assert-LastExit "Telechargement du modele Ollama incomplet."
  Set-Config "OLLAMA_MODEL" $model
  Set-Config "OLLAMA_ENABLED" "true"
  & docker compose --env-file $envFile @compose up -d --build api web
  Assert-LastExit "Impossible de redemarrer l'API avec le modele local."

  Write-Host ""
  Write-Host "IA locale prete : http://localhost:8501 -> Pour moi -> Mon conseiller."
  Write-Host "Les recommandations proviennent toujours du catalogue PostgreSQL."
  Write-Host "En cas de modele indisponible, le conseiller guide prend le relais."
}
finally {
  Pop-Location
}
