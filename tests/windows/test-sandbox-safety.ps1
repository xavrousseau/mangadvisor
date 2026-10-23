# Real Windows PowerShell subprocesses; Docker/HTTP are intercepted before use.
param([switch]$ValidateCompose)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
. (Join-Path $repo 'cmd/environment-safety.ps1')
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('ma_safety_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
$root=Join-Path $fixture 'mangadvisor-test'
New-Item -ItemType Directory -Path (Join-Path $root 'cmd') -Force | Out-Null
Copy-Item -Path (Join-Path $repo 'cmd/*.ps1') -Destination (Join-Path $root 'cmd')
Copy-Item -LiteralPath (Join-Path $repo 'mangadvisor.cmd') -Destination $root
Copy-Item -LiteralPath (Join-Path $repo '.env.example') -Destination $root
New-Item -ItemType Directory -Path (Join-Path $root 'infra/compose') -Force | Out-Null
Copy-Item -Path (Join-Path $repo 'infra/compose/*.yml') -Destination (Join-Path $root 'infra/compose')
$envPath=Join-Path $root '.env'
[IO.File]::WriteAllText($envPath,"POSTGRES_DB=production`nAPI_PORT=8000`n")
$originalHash=(Get-FileHash -LiteralPath $envPath).Hash
$configPath=Join-Path $fixture 'resolved.json'
$marker=Join-Path $fixture 'mutation.txt'
$runner=Join-Path $fixture 'runner.ps1'
$runnerSource=@'
param([string]$Root,[string]$Script,[string]$Action,[string]$Config,[string]$Marker)
$ErrorActionPreference='Stop'
function docker {
  $global:LASTEXITCODE=0
  if ($args -contains 'config') { Get-Content -LiteralPath $Config -Raw; return }
  if ($args[0] -eq 'info') { 'fixture'; return }
  if ($args[0] -eq 'compose' -and $args[1] -eq 'version') { 'fixture'; return }
  [IO.File]::AppendAllText($Marker,'docker mutation attempted')
  throw 'Unexpected Docker mutation'
}
function Invoke-RestMethod {
  [IO.File]::AppendAllText($Marker,'HTTP attempted')
  throw 'Unexpected HTTP'
}
function Start-Process {
  [IO.File]::AppendAllText($Marker,'process attempted')
  throw 'Unexpected process'
}
try {
  $global:LASTEXITCODE=0
  $path=Join-Path $Root ('cmd/'+$Script)
  if ($Action) { & $path -Action $Action } else { & $path }
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  exit 0
} catch {
  if ($_.Exception.Message -like 'SANDBOX_SAFETY:*') { Write-Output 'SAFE_REFUSAL'; exit 23 }
  Write-Output $_.Exception.Message
  exit 24
}
'@
[IO.File]::WriteAllText($runner,$runnerSource,[Text.Encoding]::ASCII)
function Invoke-Refused([string]$Script,[string]$Action='') {
  $previous=$ErrorActionPreference
  $parameters=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-Root',$root,'-Script',$Script,'-Config',$configPath,'-Marker',$marker)
  if ($Action) { $parameters+=@('-Action',$Action) }
  try {
    $ErrorActionPreference='Continue'
    $output=@(& powershell.exe @parameters 2>&1)
    $code=$LASTEXITCODE
  } finally { $ErrorActionPreference=$previous }
  if (-not (($code -eq 23 -and ($output -join '') -match 'SAFE_REFUSAL') -or
      ($code -eq 1 -and ($output -join '') -match 'SANDBOX_SAFETY:'))) {
    throw "Expected safety refusal from $Script/$Action : $output"
  }
  if (Test-Path -LiteralPath $marker) { throw 'A mutation preceded the refusal.' }
  if ((Get-FileHash -LiteralPath $envPath).Hash -cne $originalHash) { throw 'Existing configuration changed.' }
  foreach ($directory in @('private-data','backups','mobile-local','data')) {
    if (Test-Path -LiteralPath (Join-Path $root $directory)) { throw "Unexpected write: $directory" }
  }
}
function New-SafeConfig {
  $result=@{name='mangadvisor_sandbox';services=@{};volumes=@{};networks=@{
    mangadvisor_network=@{name='mangadvisor_sandbox_network'}}}
  foreach ($name in @('postgres','meilisearch','api','web','engine','catalog-sync','ollama')) {
    $service=@{container_name=('mangadvisor_sandbox_'+$name.Replace('-','_'));networks=@{mangadvisor_network=$null}}
    if ($name -in @('postgres','api','engine','catalog-sync')) {
      $db=if ($name -eq 'api') {'mangadvisor_realtest'} else {'mangadvisor_sandbox'}
      $service.environment=@{POSTGRES_DB=$db;POSTGRES_USER='manga_sandbox';POSTGRES_HOST='postgres';POSTGRES_PORT='5432'}
    }
    $result.services[$name]=$service
  }
  foreach ($spec in @(
    @('postgres','mangadvisor_pgdata','/var/lib/postgresql/data'),
    @('meilisearch','mangadvisor_meili','/meili_data'),
    @('ollama','mangadvisor_ollama_models','/root/.ollama'),
    @('engine','manga_sandbox_raw','/workspace/data/raw'),
    @('engine','manga_sandbox_logs','/workspace/data/logs'),
    @('catalog-sync','manga_sandbox_raw','/workspace/data/raw'),
    @('catalog-sync','manga_sandbox_logs','/workspace/data/logs'))) {
    $result.volumes[$spec[1]]=@{name=('mangadvisor_sandbox_'+$spec[1])}
    if (-not $result.services[$spec[0]].ContainsKey('volumes')) { $result.services[$spec[0]].volumes=@() }
    $result.services[$spec[0]].volumes+=@{type='volume';source=$spec[1];target=$spec[2]}
  }
  return $result
}
$savedEnvironment=@{}
try {
  foreach ($key in @('COMPOSE_PROJECT_NAME','COMPOSE_FILE','COMPOSE_ENV_FILES','POSTGRES_DB','POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_PORT','MEILI_MASTER_KEY','MEILI_PORT','API_PORT','UI_PORT')) {
    $savedEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)
    [Environment]::SetEnvironmentVariable($key,$null)
  }
  foreach ($action in @('Environment','Start','Stop','Update','Database','Inventory')) {
    Invoke-Refused 'control-center.ps1' $action
  }
  foreach ($script in @('library-backup.ps1','ai-setup.ps1','mobile-setup.ps1','import-private-inventory.ps1','benchmark-mangatheque.ps1')) {
    Invoke-Refused $script
  }
  # Positive control: the stable Environment action still works in its own clone.
  $stableRoot=Join-Path $fixture 'stable-clone'
  New-Item -ItemType Directory -Path (Join-Path $stableRoot 'cmd') -Force | Out-Null
  Copy-Item -Path (Join-Path $repo 'cmd/*.ps1') -Destination (Join-Path $stableRoot 'cmd')
  $sample=[IO.File]::ReadAllText((Join-Path $repo '.env.example')).Replace('changeme','synthetic-fixture-secret')
  [IO.File]::WriteAllText((Join-Path $stableRoot '.env'),$sample)
  $stableHash=(Get-FileHash -LiteralPath (Join-Path $stableRoot '.env')).Hash
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -Root $stableRoot -Script control-center.ps1 -Action Environment -Config $configPath -Marker $marker
  if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $marker)) { throw 'Stable initialization regressed.' }
  if ((Get-FileHash -LiteralPath (Join-Path $stableRoot '.env')).Hash -cne $stableHash) { throw 'Stable settings overwritten.' }
  # The marker survives renaming a sandbox checkout.
  [IO.File]::WriteAllText((Join-Path $root '.env.sandbox'),'POSTGRES_DB=production')
  $renamed=Join-Path $fixture 'renamed-clone'
  Move-Item -LiteralPath $root -Destination $renamed
  $root=$renamed
  $envPath=Join-Path $root '.env'
  Invoke-Refused 'control-center.ps1' 'Environment'
  # No sandbox marker: stable initialization remains available in an ordinary clone.
  Remove-Item -LiteralPath (Join-Path $root '.env.sandbox')
  Assert-MangadvisorStableCheckout $root
  $env:COMPOSE_PROJECT_NAME='mangadvisor_sandbox'
  Invoke-Refused 'control-center.ps1' 'Environment'
  [Environment]::SetEnvironmentVariable('COMPOSE_PROJECT_NAME',$null)
  $renamed=Join-Path $fixture 'mangadvisor-test'
  Move-Item -LiteralPath $root -Destination $renamed
  $root=$renamed
  $envPath=Join-Path $root '.env'

  $safe=New-SafeConfig
  Assert-MangadvisorSandboxConfig (ConvertFrom-Json ($safe | ConvertTo-Json -Depth 20))
  $changes=@(
    {param($c) $c.name='mangadvisor'},
    {param($c) $c.services.postgres.container_name='mangadvisor_postgres'},
    {param($c) $c.volumes.mangadvisor_pgdata.name='mangadvisor_mangadvisor_pgdata'},
    {param($c) $c.volumes.mangadvisor_pgdata.external=$true},
    {param($c) $c.volumes.mangadvisor_pgdata.driver_opts=@{device='/production';type='none';o='bind'}},
    {param($c) $c.networks.mangadvisor_network.name='mangadvisor_network'},
    {param($c) $c.services.engine.volumes[0].source='mangadvisor_pgdata'},
    {param($c) $c.services.engine.volumes[0].type='bind'},
    {param($c) $c.services.api.environment.POSTGRES_DB='production'},
    {param($c) $c.services.api.environment.POSTGRES_HOST='host.docker.internal'},
    {param($c) $c.services.api.ports=@(@{host_ip='127.0.0.1';target=8000;published='8000'})},
    {param($c) $c.services.api.ports=@(@{host_ip='0.0.0.0';target=8000;published='18000'})},
    {param($c) $c.services.api.network_mode='host'},
    {param($c) $c.services.api.volumes_from=@('mangadvisor_api')},
    {param($c) $c.services.api.privileged=$true},
    {param($c) $c.services.foreign=@{container_name='production'}}
  )
  foreach ($change in $changes) {
    $bad=New-SafeConfig
    & $change $bad
    [IO.File]::WriteAllText($configPath,($bad | ConvertTo-Json -Depth 20))
    # Setup must reject BEFORE creating its .env.sandbox.
    Invoke-Refused 'setup-sandbox.ps1'
    $sandboxFile=Join-Path $root '.env.sandbox'
    if (Test-Path -LiteralPath $sandboxFile) { throw 'Setup wrote before validation.' }
    [IO.File]::WriteAllText($sandboxFile,'synthetic fixture')
    Invoke-Refused 'control-center.ps1' 'BibliographyAcceptance'
    Remove-Item -LiteralPath $sandboxFile
  }
  # A good configuration reaches setup's sole authorized write, then stays unchanged.
  [IO.File]::WriteAllText($configPath,($safe | ConvertTo-Json -Depth 20))
  foreach ($attempt in 1..2) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -Root $root -Script setup-sandbox.ps1 -Config $configPath -Marker $marker
    if ($LASTEXITCODE -ne 0) { throw 'Safe setup refused.' }
    $hash=(Get-FileHash -LiteralPath (Join-Path $root '.env.sandbox')).Hash
    if ($attempt -eq 1) { $first=$hash } elseif ($hash -cne $first) { throw 'Existing sandbox secrets replaced.' }
  }
  if ($ValidateCompose) {
    # Actual CLI rendering only: synthetic environment, no daemon or real .env.
    $env:POSTGRES_DB='mangadvisor_sandbox'; $env:POSTGRES_USER='manga_sandbox'
    $env:POSTGRES_PASSWORD='synthetic'; $env:MEILI_MASTER_KEY='synthetic'
    $env:POSTGRES_PORT='15432'; $env:MEILI_PORT='17700'; $env:API_PORT='18000'; $env:UI_PORT='18501'
    foreach ($local in @($false,$true)) {
      $arguments=@('compose','--env-file',(Join-Path $repo '.env.example'),'-f',(Join-Path $repo 'infra/compose/docker-compose.yml'))
      if ($local) { $arguments+=@('-f',(Join-Path $repo 'infra/compose/docker-compose.local.yml')) }
      $arguments+=@('-f',(Join-Path $repo 'infra/compose/docker-compose.sandbox.yml'))
      Assert-MangadvisorSandboxCompose $arguments
    }
    # Actual Compose environment precedence must not defeat the validator.
    foreach ($override in @(@('COMPOSE_PROJECT_NAME','mangadvisor'),@('API_PORT','8000'))) {
      $old=[Environment]::GetEnvironmentVariable($override[0])
      try {
        [Environment]::SetEnvironmentVariable($override[0],$override[1])
        $refused=$false
        try { Assert-MangadvisorSandboxCompose $arguments }
        catch {
          if ($_.Exception.Message -notlike 'SANDBOX_SAFETY:*') { throw }
          $refused=$true
        }
        if (-not $refused) { throw ('Inherited production override accepted: '+$override[0]) }
      } finally { [Environment]::SetEnvironmentVariable($override[0],$old) }
    }
    Write-Host 'OK: actual Docker Compose rendering (base + sandbox, base + local + sandbox).'
    Write-Host 'OK: inherited production project and API port rejected by actual Compose validation.'
  }
  Write-Host ('OK: stable entry points blocked; '+$changes.Count+' unsafe configurations rejected by setup and recipe before mutation; safe setup idempotent.')
} finally {
  foreach ($key in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($key,$savedEnvironment[$key]) }
  # Cleanup only this newly created synthetic fixture under the OS temp directory.
  $absolute=[IO.Path]::GetFullPath($fixture)
  $tempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
  if (-not $absolute.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase) -or
      (Split-Path $absolute -Leaf) -notmatch '^ma_safety_[a-f0-9]{32}$') { throw 'Unsafe fixture cleanup path.' }
  Remove-Item -LiteralPath $absolute -Recurse -Force
}
