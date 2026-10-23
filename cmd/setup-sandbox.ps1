# Prepare an independent local test configuration; does NOT start containers.
# Run only from the dedicated mangadvisor-test checkout.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "environment-safety.ps1")
if ((Split-Path $root -Leaf) -ne "mangadvisor-test") {
  throw "Safety stop: this script runs only from a folder named mangadvisor-test."
}
$sample = Join-Path $root ".env.example"
$target = Join-Path $root ".env.sandbox"
if (!(Test-Path -LiteralPath $sample -PathType Leaf)) {
  throw "Missing .env.example"
}
$create=!(Test-Path -LiteralPath $target -PathType Leaf)
if ($create) {
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
} else {
  Write-Host "Existing .env.sandbox preserved (secrets unchanged)."
}

$envLines=if ($create) { @($settings -split '\r?\n') } else { @(Get-Content -LiteralPath $target) }
foreach ($pair in @("POSTGRES_DB=mangadvisor_sandbox", "POSTGRES_USER=manga_sandbox",
                   "POSTGRES_PORT=15432", "MEILI_PORT=17700",
                   "API_PORT=18000", "UI_PORT=18501")) {
  $key=$pair.Split('=')[0]
  $entries=@($envLines | Where-Object { $_ -match ('^\s*'+[regex]::Escape($key)+'\s*=') })
  if ($entries.Count -ne 1 -or $entries[0] -cne $pair) {
    throw "SANDBOX_SAFETY: unsafe or duplicate sandbox setting for $key"
  }
}
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker Desktop must be installed; no containers have been started."
}
$base = Join-Path $root "infra/compose/docker-compose.yml"
$local = Join-Path $root "infra/compose/docker-compose.local.yml"
$sandbox = Join-Path $root "infra/compose/docker-compose.sandbox.yml"
$configFile=if ($create) { $sample } else { $target }
$composeArgs = @("compose", "--env-file", $configFile, "-f", $base,
                 "-f", $local, "-f", $sandbox)
$saved=@{}
try {
  if ($create) {
    # Render with generated settings in this process only. No config file is
    # created before validation; inherited Compose overrides remain visible.
    foreach ($key in $values.Keys) {
      $saved[$key]=[Environment]::GetEnvironmentVariable($key)
      [Environment]::SetEnvironmentVariable($key,$values[$key])
    }
  }
  Assert-MangadvisorSandboxCompose $composeArgs
} finally {
  foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key,$saved[$key]) }
}
if ($create) {
  # CreateNew refuses a file appearing concurrently; never overwrite secrets.
  $stream=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
  try {
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($settings)
    $stream.Write($bytes,0,$bytes.Length)
  } finally { $stream.Dispose() }
  Write-Host "Independent .env.sandbox created after validation."
}
Write-Host "Sandbox configuration OK. No containers started."
Write-Host "Ports: Web 18501, API 18000, Postgres 15432, Meili 17700."
Write-Host "Use docker compose with the three Compose files and .env.sandbox."
