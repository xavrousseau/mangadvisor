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

function Assert-MangadvisorSandboxConfig($Config) {
  # Read properties without relying on the caller's StrictMode setting.
  function Value($Object,[string]$Key) {
    if ($null -eq $Object) { return $null }
    $property=$Object.PSObject.Properties[$Key]
    if ($null -ne $property) { return $property.Value }
    return $null
  }
  function Require([bool]$Condition,[string]$Message) {
    if (-not $Condition) { throw "SANDBOX_SAFETY: $Message" }
  }
  Require ((Value $Config 'name') -ceq 'mangadvisor_sandbox') 'projet Compose non sandbox.'
  $services=Value $Config 'services'
  $expected=@('postgres','meilisearch','api','web','engine','catalog-sync','ollama')
  Require ($null -ne $services) 'services absents.'
  Require (@($services.PSObject.Properties).Count -eq $expected.Count) 'services inattendus.'
  $volumes=Value $Config 'volumes'
  $allowedVolumes=@('mangadvisor_pgdata','mangadvisor_meili','mangadvisor_ollama_models','manga_sandbox_raw','manga_sandbox_logs')
  Require ($null -ne $volumes) 'volumes absents.'
  Require (@($volumes.PSObject.Properties).Count -eq $allowedVolumes.Count) 'volumes inattendus.'
  foreach ($key in $allowedVolumes) {
    $volume=Value $volumes $key
    Require ($null -ne $volume) 'volume sandbox manquant.'
    Require ((Value $volume 'name') -ceq ('mangadvisor_sandbox_'+$key)) 'volume de production ou nom non sandbox.'
    Require (-not (Value $volume 'external')) 'volume externe interdit.'
    Require (-not (Value $volume 'driver_opts')) 'options de montage de volume interdites.'
    $driver=Value $volume 'driver'
    Require (-not $driver -or $driver -ceq 'local') 'pilote de volume interdit.'
  }
  $networks=Value $Config 'networks'
  Require ($null -ne $networks) 'reseaux absents.'
  Require (@($networks.PSObject.Properties).Count -eq 1) 'reseaux inattendus.'
  $network=Value $networks 'mangadvisor_network'
  Require ((Value $network 'name') -ceq 'mangadvisor_sandbox_network') 'reseau non sandbox.'
  Require (-not (Value $network 'external')) 'reseau externe interdit.'
  $mounts=@{
    postgres=@{'/var/lib/postgresql/data'='mangadvisor_pgdata'}
    meilisearch=@{'/meili_data'='mangadvisor_meili'}
    ollama=@{'/root/.ollama'='mangadvisor_ollama_models'}
    engine=@{'/workspace/data/raw'='manga_sandbox_raw';'/workspace/data/logs'='manga_sandbox_logs'}
    'catalog-sync'=@{'/workspace/data/raw'='manga_sandbox_raw';'/workspace/data/logs'='manga_sandbox_logs'}
  }
  $ports=@{postgres=@('5432','15432');meilisearch=@('7700','17700');api=@('8000','18000');web=@('80','18501')}
  foreach ($name in $expected) {
    $service=Value $services $name
    Require ($null -ne $service) 'service sandbox manquant.'
    Require ((Value $service 'container_name') -ceq ('mangadvisor_sandbox_'+$name.Replace('-','_'))) 'conteneur non sandbox.'
    Require (-not (Value $service 'network_mode')) 'network_mode interdit.'
    Require (-not (Value $service 'volumes_from')) 'volumes_from interdit.'
    Require (-not (Value $service 'privileged')) 'conteneur privilegie interdit.'
    Require (-not (Value $service 'devices')) 'peripheriques hote interdits.'
    $attached=Value $service 'networks'
    Require ($null -ne $attached) 'reseau de service absent.'
    Require (@($attached.PSObject.Properties).Count -eq 1 -and $null -ne $attached.PSObject.Properties['mangadvisor_network']) 'reseau de service non sandbox.'
    $expectedMounts=@{}
    if ($mounts.ContainsKey($name)) { $expectedMounts=$mounts[$name] }
    $actualMounts=@(Value $service 'volumes' | Where-Object { $null -ne $_ })
    Require ($actualMounts.Count -eq $expectedMounts.Count) 'nombre de montages inattendu.'
    $seen=@{}
    foreach ($mount in $actualMounts) {
      $target=[string](Value $mount 'target')
      Require ((Value $mount 'type') -ceq 'volume') 'bind mount interdit en sandbox.'
      Require ($expectedMounts.ContainsKey($target) -and -not $seen.ContainsKey($target)) 'cible de montage inattendue.'
      Require ((Value $mount 'source') -ceq $expectedMounts[$target]) 'source de montage non sandbox.'
      $seen[$target]=$true
    }
    $actualPorts=@(Value $service 'ports' | Where-Object { $null -ne $_ })
    Require ($actualPorts.Count -le 1) 'ports supplementaires interdits.'
    foreach ($port in $actualPorts) {
      Require ($ports.ContainsKey($name)) 'port publie sur un service interne.'
      Require ((Value $port 'host_ip') -ceq '127.0.0.1' -and
        [string](Value $port 'target') -ceq $ports[$name][0] -and
        [string](Value $port 'published') -ceq $ports[$name][1]) 'port de production ou interface non locale.'
    }
    if ($name -in @('postgres','api','engine','catalog-sync')) {
      $envConfig=Value $service 'environment'
      $db=if ($name -ceq 'api') { 'mangadvisor_realtest' } else { 'mangadvisor_sandbox' }
      Require ((Value $envConfig 'POSTGRES_DB') -ceq $db) 'base SQL non sandbox.'
      Require ((Value $envConfig 'POSTGRES_USER') -ceq 'manga_sandbox') 'role SQL non sandbox.'
      if ($name -cne 'postgres') {
        Require ((Value $envConfig 'POSTGRES_HOST') -ceq 'postgres' -and [string](Value $envConfig 'POSTGRES_PORT') -ceq '5432') 'connexion SQL externe interdite.'
      }
    }
  }
}

function Assert-MangadvisorSandboxCompose([string[]]$Arguments) {
  # config renders locally; never starts a container. Do not print resolved secrets.
  $resolved=@(& docker @Arguments --profile automation --profile ai config --format json 2>$null)
  if ($LASTEXITCODE -ne 0) { throw 'SANDBOX_SAFETY: resolution Compose impossible.' }
  try { $config=ConvertFrom-Json -InputObject ($resolved -join [Environment]::NewLine) -ErrorAction Stop }
  catch { throw 'SANDBOX_SAFETY: configuration Compose JSON invalide.' }
  Assert-MangadvisorSandboxConfig $config
}
