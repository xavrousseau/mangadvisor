# Mangadvisor Mobile - private Wi-Fi HTTPS, only when explicitly enabled.
param([switch]$Stop)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$compose = @("-f", (Join-Path $root "infra\compose\docker-compose.yml"),
             "-f", (Join-Path $root "infra\compose\docker-compose.dev.yml"),
             "-f", (Join-Path $root "infra\compose\docker-compose.mobile.yml"))
$envFile = Join-Path $root ".env"
$mobileEnv = Join-Path $root ".env.mobile"
$accessFile = Join-Path $root "mobile-local\access.txt"
$caFile = Join-Path $root "mobile-local\mangadvisor-root-ca.crt"
function Assert-Exit([string]$label) {
  if ($LASTEXITCODE -ne 0) { throw "$label (code $LASTEXITCODE)." }
}
if (!(Test-Path $envFile)) { throw "Le fichier .env manque. Installe Mangadvisor normalement avant." }
docker info --format "{{.ServerVersion}}" 1>$null 2>$null
Assert-Exit "Docker Desktop doit etre demarre"
if ($Stop) {
  if (!(Test-Path $mobileEnv)) { Write-Host "Acces mobile non configure."; exit 0 }
  & docker compose --env-file $envFile --env-file $mobileEnv @compose stop mobile_https
  Assert-Exit "Impossible d'arreter le proxy mobile"
  Write-Host "Acces mobile HTTPS arrete, donnees conservees."
  exit 0
}
$addresses = @(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
  ForEach-Object {
    $name = $_.InterfaceAlias
    foreach ($entry in $_.IPv4Address) {
      $ip = [string]$entry.IPAddress
      $o = $ip.Split(".")
      if ($o.Count -ne 4) { continue }
      $private = ($o[0] -eq "10") -or ($o[0] -eq "192" -and $o[1] -eq "168") -or
        ($o[0] -eq "172" -and [int]$o[1] -ge 16 -and [int]$o[1] -le 31)
      if ($private -and $name -notmatch "vEthernet|WSL|Docker|Virtual|Loopback") {
        [pscustomobject]@{ IP = $ip; Interface = $name }
      }
    }
  })
if (!$addresses.Count) {
  throw "Pas d'IPv4 privee valide. Connecte PC et telephone au meme Wi-Fi."
}
Write-Host "Reseaux detectes :"
for ($i=0; $i -lt $addresses.Count; $i++) {
  Write-Host "  $($i+1) - $($addresses[$i].IP) ($($addresses[$i].Interface))"
}
$choice=1
if ($addresses.Count -gt 1) {
  $raw=Read-Host "Numero du reseau Wi-Fi/Ethernet [1]"
  if ($raw) {
    $number=0
    if (![int]::TryParse($raw,[ref]$number) -or $number -lt 1 -or $number -gt $addresses.Count) {
      throw "Numero invalide."
    }
    $choice=$number
  }
}
$ip=$addresses[$choice-1].IP
New-Item -ItemType Directory -Force -Path (Split-Path $accessFile -Parent) | Out-Null
if (!(Test-Path $mobileEnv) -or !(Test-Path $accessFile)) {
  $bytes=New-Object byte[] 18
  $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $password=[BitConverter]::ToString($bytes).Replace("-","").ToLowerInvariant()
  # Feed password via stdin, never via command-line args.
  $lines=@($password | docker run --rm -i caddy:2.10-alpine caddy hash-password --algorithm bcrypt)
  Assert-Exit "Creation du hash de mot de passe impossible"
  $hash=[string]($lines | Select-Object -Last 1)
  if ($hash -notmatch '^\$2[aby]\$') { throw "Empreinte bcrypt invalide." }
  Set-Content -Path $mobileEnv -Value @("MANGADVISOR_LAN_IP=$ip", "MOBILE_PASSWORD_HASH='$hash'") -Encoding Ascii
  Set-Content -Path $accessFile -Value @(
    "Mangadvisor Mobile - informations privees a conserver sur ce PC",
    "Adresse : https://$($ip):8443",
    "Utilisateur : manga",
    "Mot de passe : $password",
    "Certificat racine : $caFile") -Encoding UTF8
} else {
  $lines=@(Get-Content $mobileEnv | Where-Object { $_ -notmatch "^MANGADVISOR_LAN_IP=" })
  Set-Content -Path $mobileEnv -Value (@("MANGADVISOR_LAN_IP=$ip") + $lines) -Encoding Ascii
  $access=@(Get-Content $accessFile | ForEach-Object {
    if ($_ -match "^Adresse :") { "Adresse : https://$($ip):8443" } else { $_ }
  })
  Set-Content -Path $accessFile -Value $access -Encoding UTF8
}
Write-Host "Demarrage Mangadvisor sur https://$($ip):8443 ..."
& docker compose --env-file $envFile --env-file $mobileEnv @compose up -d --build mobile_https
Assert-Exit "Echec du lancement HTTPS"
$exported=$false
for ($i=0; $i -lt 15; $i++) {
  docker cp "mangadvisor_mobile_https:/data/caddy/pki/authorities/local/root.crt" $caFile 2>$null
  if ($LASTEXITCODE -eq 0 -and (Test-Path $caFile)) { $exported=$true;break }
  Start-Sleep -Seconds 2
}
if (!$exported) { throw "Le certificat racine n'a pas ete genere. Lis les logs du proxy." }
Write-Host ""
Write-Host "======= MANGADVISOR MOBILE PRET ======="
Write-Host "URL : https://$($ip):8443"
Write-Host "Identifiant : manga"
Write-Host "Mot de passe et URL : $accessFile"
Write-Host "Certificat PUBLIC Android : $caFile"
Write-Host ""
Write-Host "1. Transfere le fichier .crt sur le telephone (USB ou Quick Share)."
Write-Host "2. Android : Parametres > Securite > Installer un certificat CA."
Write-Host "3. Ouvre le lien HTTPS dans Chrome, identifie-toi, autorise la camera."
Write-Host "4. Si inaccessible, verifier le Wi-Fi commun et le pare-feu Windows (TCP 8443, profil Prive)."
Write-Host "Ne partage pas access.txt ni les cles privees Caddy."
