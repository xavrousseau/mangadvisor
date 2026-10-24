# Shared fail-closed checks. Loading this file never contacts Docker or writes files.
function Assert-MangadvisorStableCheckout([string]$Root) {
  $leaf=Split-Path $Root -Leaf
  if ($leaf -match '(?i)(^|[-_])(test|sandbox)([-_]|$)' -or
      (Test-Path -LiteralPath (Join-Path $Root '.env.sandbox'))) {
    throw 'SANDBOX_SAFETY: outil stable interdit dans ce clone de test. Utiliser la configuration sandbox validee ; aucune action effectuee.'
  }
  foreach ($key in @('COMPOSE_FILE','COMPOSE_ENV_FILES','COMPOSE_PROJECT_NAME')) {
    $value=[Environment]::GetEnvironmentVariable($key)
    if ($value -and ($key -ne 'COMPOSE_PROJECT_NAME' -or $value -cne 'mangadvisor')) {
      throw "SANDBOX_SAFETY: variable $key incompatible avec le ciblage stable explicite."
    }
  }
}
