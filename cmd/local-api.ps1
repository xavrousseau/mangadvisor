# Read the configured localhost API port for Windows inventory tools.
# Intentionally accepts only a numeric local TCP port; never a remote host.
function Get-MangadvisorApiUrl([string]$EnvFile) {
  if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Fichier .env introuvable. Lance mangadvisor.cmd option 1 (premiere installation)."
  }
  $matchesInFile=@(Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^\s*API_PORT\s*=' })
  if ($matchesInFile.Count -eq 0) {
    throw "API_PORT absent du fichier .env."
  }
  $raw=([string]$matchesInFile[-1]).Split("=",2)[1].Trim().Trim("'").Trim('"')
  $port=0
  if (-not [int]::TryParse($raw,[ref]$port) -or $port -lt 1 -or $port -gt 65535) {
    throw "API_PORT invalide dans .env : un port entre 1 et 65535 est requis."
  }
  return "http://127.0.0.1:$port"
}
