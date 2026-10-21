# Prepare an independent local test configuration; does NOT start containers.
# Run only from the dedicated mangadvisor-test checkout.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ((Split-Path $root -Leaf) -ne "mangadvisor-test") {
  throw "Safety stop: this script runs only from a folder named mangadvisor-test."
}
$sample = Join-Path $root ".env.example"
$target = Join-Path $root ".env.sandbox"
if (!(Test-Path -LiteralPath $sample -PathType Leaf)) {
  throw "Missing .env.example"
}
if (!(Test-Path -LiteralPath $target -PathType Leaf)) {
  $settings = [IO.File]::ReadAllText($sample, [Text.Encoding]::UTF8)
  function New-Key {
    $bytes = New-Object byte[] 28
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
  }
  $values = @{
    "POSTGRES_DB"="mangadvisor_sandbox"
    "POSTGRES_USER"="manga_sandbox"
    "POSTGRES_PASSWORD"=(New-Key)
    "POSTGRES_PORT"="15432"
    "MEILI_MASTER_KEY"=(New-Key)
    "MEILI_PORT"="17700"
    "API_PORT"="18000"
    "UI_PORT"="18501"
  }
  foreach ($key in $values.Keys) {
    $pattern = "(?m)^" + [regex]::Escape($key) + "=.*$"
    if (-not [regex]::IsMatch($settings, $pattern)) {
      throw "Missing variable in .env.example: $key"
    }
    $settings = [regex]::Replace($settings, $pattern, ($key + "=" + $values[$key]))
  }
  [IO.File]::WriteAllText($target, $settings, (New-Object Text.UTF8Encoding($false)))
  Write-Host "Independent .env.sandbox created."
} else {
  Write-Host "Existing .env.sandbox preserved (secrets unchanged)."
}

$envLines = @(Get-Content -LiteralPath $target)
foreach ($pair in @("POSTGRES_DB=mangadvisor_sandbox", "POSTGRES_USER=manga_sandbox",
                   "POSTGRES_PORT=15432", "MEILI_PORT=17700",
                   "API_PORT=18000", "UI_PORT=18501")) {
  if ($pair -notin $envLines) { throw "Unsafe sandbox setting: expected $pair" }
}
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker Desktop must be installed; no containers have been started."
}
$base = Join-Path $root "infra/compose/docker-compose.yml"
$local = Join-Path $root "infra/compose/docker-compose.local.yml"
$sandbox = Join-Path $root "infra/compose/docker-compose.sandbox.yml"
$composeArgs = @("compose", "--env-file", $target, "-f", $base,
                 "-f", $local, "-f", $sandbox)
$resolved = & docker @($composeArgs + @("--profile", "automation", "--profile", "ai", "config", "--format", "json"))
if ($LASTEXITCODE -ne 0) { throw "Sandbox Compose config failed." }
$config = (($resolved -join [Environment]::NewLine) | ConvertFrom-Json)
if ($config.name -ne "mangadvisor_sandbox") { throw "Wrong Compose project name." }
foreach ($name in @("postgres", "meilisearch", "api", "web",
                   "engine", "catalog-sync", "ollama")) {
  $expected = "mangadvisor_sandbox_" + ($name -replace "-", "_")
  if ($name -eq "catalog-sync") { $expected = "mangadvisor_sandbox_catalog_sync" }
  $service = $config.services.PSObject.Properties[$name]
  if ($null -eq $service -or $service.Value.container_name -ne $expected) {
    throw "Unsafe container name for $name"
  }
}
if ($config.networks.mangadvisor_network.name -ne "mangadvisor_sandbox_network") {
  throw "Wrong Docker network."
}
$expectedVolumes = @("mangadvisor_sandbox_mangadvisor_pgdata",
                     "mangadvisor_sandbox_mangadvisor_meili",
                     "mangadvisor_sandbox_mangadvisor_ollama_models")
foreach ($volume in $expectedVolumes) {
  $found = @($config.volumes.PSObject.Properties | Where-Object { $_.Value.name -eq $volume })
  if ($found.Count -ne 1) { throw "Unsafe Docker volume mapping: $volume" }
}
Write-Host "Sandbox configuration OK. No containers started."
Write-Host "Ports: Web 18501, API 18000, Postgres 15432, Meili 17700."
Write-Host "Use docker compose with the three Compose files and .env.sandbox."
