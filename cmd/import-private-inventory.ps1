# Mangadvisor 3.8  -  safe import of a private physical collection.
# Windows PowerShell 5.1/7. All requests go ONLY to loopback.
param([string]$CsvFile="",[switch]$PreviewOnly,[switch]$CiApply)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$private=Join-Path $root "private-data"
if (-not $CsvFile) { $CsvFile=Join-Path $private "mangatheque.csv" }
if (-not (Test-Path -LiteralPath $CsvFile -PathType Leaf)) {
  throw "Fichier introuvable : $CsvFile. Place le CSV dans private-data/mangatheque.csv."
}
if (-not (Test-Path -LiteralPath $private)) {
  New-Item -ItemType Directory -Path $private -Force | Out-Null
}
$api="http://127.0.0.1:8000"
$health=Invoke-RestMethod -Uri "$api/health" -TimeoutSec 20
if ($health.status -ne "ok") { throw "Base Mangadvisor indisponible." }
$csv=[IO.File]::ReadAllText([IO.Path]::GetFullPath($CsvFile),[Text.Encoding]::UTF8)
$body=@{csv_content=$csv} | ConvertTo-Json -Depth 5 -Compress
$preview=Invoke-RestMethod -Method Post -Uri "$api/inventory/preview" -TimeoutSec 120 -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
$path=Join-Path $private ("inventaire_apercu_{0}_{1}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"),([guid]::NewGuid().ToString("N")).Substring(0,6))
$preview | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $path -Encoding UTF8
Write-Host ""
Write-Host "========= MANGADVISOR 4.3  -  APERCU SANS ECRITURE ========="
Write-Host "Fichier : $CsvFile"
Write-Host "Quantites physiques declarees : $($preview.declared_physical_volumes)"
Write-Host "Nouvelles declarations fiables : $($preview.ready)"
Write-Host "Deja presentes sans changement : $($preview.unchanged)"
Write-Host "A examiner manuellement : $($preview.review)"
Write-Host "Rapport local prive : $path"
foreach($entry in @($preview.items | Where-Object {$_.status -like "REVIEW_*"} | Select-Object -First 25)) {
  Write-Host ("[A VERIFIER] ligne {0}: {1}  -  {2}" -f $entry.line,$entry.entry_title,$entry.status)
}
foreach($entry in @($preview.items | Where-Object {$_.status -eq "READY"} | Select-Object -First 6)) {
  $format=if($entry.edition_declared){$entry.edition_declared}else{"edition non precisee"}
  Write-Host ("[PRET] {0}  -  {1} ({2} tomes principaux)" -f $entry.catalog_title,$format,$entry.main_volumes)
}
if ($PreviewOnly) {
  Write-Host "Mode APERCU : aucune modification de la base."
  exit 0
}
# Unmatched works are preserved ONLY after a second, separate user decision.
# They are not associated with a manga_id and never affect recommendations.
$unresolved=@($preview.items | Where-Object {
  $_.status -eq "REVIEW_MISSING" -or $_.status -eq "REVIEW_AMBIGUOUS"
})
if (-not $CiApply -and $unresolved.Count -gt 0) {
  Write-Host ""
  Write-Host "$($unresolved.Count) entrees restent inconnues ou ambigues dans le catalogue."
  Write-Host "Tu peux les conserver en attente, sans ISBN, sans attribution a une serie et sans modification des suivis."
  $saveExpected="CONSERVER $($unresolved.Count)"
  $saveAnswer=Read-Host "Saisis exactement '$saveExpected' pour sauvegarder ces entrees en attente, ou Entree pour ignorer"
  if ($saveAnswer -ceq $saveExpected) {
    $pendingBody=@{
      csv_content=$csv
      confirmation_token=[string]$preview.confirmation_token
    } | ConvertTo-Json -Compress
    $saved=Invoke-RestMethod -Method Post -Uri "$api/inventory/pending/save" -TimeoutSec 120 -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($pendingBody))
    if ($saved.status -ne "ok" -or $saved.preserved_without_guessing -ne $true) {
      throw "Sauvegarde des entrees sans correspondance non certifiee."
    }
    Write-Host ("PRESERVEES : {0} nouvelles declarations en attente ; {1} deja presentes. Aucun manga ni ISBN ajoute." -f $saved.saved,$saved.unchanged_pending)
  } else {
    Write-Host "Conservation des entrees en attente ignoree : aucune ecriture pour ces lignes."
  }
}
if ($preview.ready -le 0) { Write-Host "Aucune nouvelle declaration fiable a importer dans les mangas."; exit 0 }
if ($CiApply) {
  if ($env:MANGADVISOR_INVENTORY_TEST_CI -ne "1" -or $health.database -ne "mangadvisor_ci") {
    throw "L'import automatise n'est autorise QUE sur la base jetable mangadvisor_ci."
  }
} else {
  if ($preview.review -gt 0) {
    Write-Warning "Certaines entrees restent non rapprochees ; elles ne seront PAS importees."
    $expected="IMPORTER $($preview.ready) PARTIEL"
  } else { $expected="IMPORTER $($preview.ready)" }
  Write-Host ""
  Write-Host "Aucun ISBN, tome lu, note ou favori n'est deduit de ce fichier."
  Write-Host "Aucun suivi existant n'est modifie. Les oeuvres absentes seront marquees POSSEDE."
  $answer=Read-Host "Saisis exactement '$expected' pour valider"
  if ($answer -cne $expected) { Write-Host "Annule : aucune ecriture."; exit 0 }
}
$applyBody=@{
  csv_content=$csv
  confirmation_token=[string]$preview.confirmation_token
  accept_partial=($preview.review -gt 0)
} | ConvertTo-Json -Compress
$result=Invoke-RestMethod -Method Post -Uri "$api/inventory/apply" -TimeoutSec 120 -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($applyBody))
if ($result.status -ne "ok" -or $result.preserved_reading_notes_scores -ne $true) {
  throw "Impossible de certifier la preservation des donnees existantes."
}
Write-Host ("RESULTAT : {0} declarations ajoutees ; {1} a verifier." -f $result.created_declarations,$result.manual_review)
Write-Host "Relance l'option 20 pour evaluer les recommandations avec la bibliotheque mise a jour."
