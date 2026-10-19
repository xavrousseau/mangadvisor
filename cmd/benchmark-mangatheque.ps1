# Mangadvisor: private, READ-ONLY catalog matching & recommendation benchmark.
# PowerShell 5.1/7. All requests go to 127.0.0.1 and include dry_run=true.
param([string]$CsvFile="")
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$privateDir=Join-Path $root "private-data"
if (-not $CsvFile) { $CsvFile=Join-Path $privateDir "mangatheque.csv" }
if (-not (Test-Path -LiteralPath $CsvFile -PathType Leaf)) {
  throw "CSV absent : copier la mangatheque extraite dans private-data/mangatheque.csv."
}
$rows=@(Import-Csv -LiteralPath $CsvFile -Delimiter ";" -Encoding UTF8)
if (-not $rows.Count) { throw "CSV vide." }
foreach($field in @("serie","tomes_principaux","doublons_identiques","autres_editions_a_identifier")) {
  if ($null -eq $rows[0].PSObject.Properties[$field]) { throw "Colonne requise : $field" }
}
# 3.7 optional edition fields; older 3.6 CSVs remain fully supported.
$hasWork=($null -ne $rows[0].PSObject.Properties["oeuvre_commune"])
$hasEdition=($null -ne $rows[0].PSObject.Properties["edition_declaree"])
if ($hasWork -ne $hasEdition) {
  throw "Renseigne oeuvre_commune et edition_declaree ensemble, ou aucune des deux colonnes."
}
$seen=@{}
$totals=@{main=0;duplicates=0;other=0}
foreach($row in $rows) {
  $title=[string]$row.serie
  if (-not $title.Trim()) { throw "Titre vide." }
  $key=$title.Trim().ToLowerInvariant()
  if ($seen.ContainsKey($key)) { throw "Titre repete, import refuse : $title" }
  $seen[$key]=$true
  if ($hasWork) {
    $work=[string]$row.oeuvre_commune
    $edition=[string]$row.edition_declaree
    if ([bool]$work.Trim() -ne [bool]$edition.Trim()) {
      throw "Edition et oeuvre commune doivent etre renseignees ensemble : $title"
    }
  }
  foreach($spec in @(@("tomes_principaux","main"),
                       @("doublons_identiques","duplicates"),
                       @("autres_editions_a_identifier","other"))) {
    $num=0
    if (-not [int]::TryParse([string]$row.($spec[0]),[ref]$num) -or $num -lt 0) {
      throw "Quantite invalide pour $title"
    }
    $totals[$spec[1]]+=$num
  }
}
$api="http://127.0.0.1:8000"
try { $health=Invoke-RestMethod -Uri "$api/health" -TimeoutSec 20 }
catch { throw "Demarre Mangadvisor avec Docker Desktop puis menu option 3 (API locale 8000)." }
if ($health.status -ne "ok") { throw "Base PostgreSQL non disponible." }
# The only CSV import call is forced dry-run: NEVER write to the live collection.
$previewRows=@($rows | ForEach-Object {
  # Same fictional work may appear twice as separately owned physical editions.
  # The matching API only understands *works*, not user-declared formats.
  # This is a dry-run; the source edition labels are retained in the report.
  $searchTitle=[string]$_.serie
  if ($hasWork -and ([string]$_.oeuvre_commune).Trim()) {
    $searchTitle=([string]$_.oeuvre_commune).Trim()
  }
  [pscustomobject]@{title=$searchTitle;library_status="OWNED";owned_volumes=$_.tomes_principaux}
})
$rawCsv=($previewRows | ConvertTo-Csv -NoTypeInformation -Delimiter ",") -join [Environment]::NewLine
$body=@{csv_content=$rawCsv;delimiter=",";default_status="OWNED";dry_run=$true} |
  ConvertTo-Json -Depth 5 -Compress
$preview=Invoke-RestMethod -Method Post -Uri "$api/library/import/csv" -TimeoutSec 120 -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
if ($preview.status -ne "dry_run") { throw "REFUS : l'API n'a pas confirme un essai sans ecriture." }
$matches=@($preview.imported_items)
$exact=@($matches | Where-Object { [int]$_.match_rank -le 2 })
$fuzzy=@($matches | Where-Object { [int]$_.match_rank -gt 2 })
# Group after the server's dry-run, using original CSV row numbers:
# two distinct declared formats of one work are NOT duplicate manga series.
$editionGroups=@()
$collisions=@()
foreach($group in @($matches | Group-Object -Property matched_manga_id | Where-Object {$_.Count -gt 1})) {
  $matched=@($group.Group)
  $sourceRows=@()
  foreach($item in $matched) {
    $index=[int]$item.line-2
    if ($index -lt 0 -or $index -ge $rows.Count) {
      throw "Incoherence du numero de ligne d'import simule."
    }
    $sourceRows+= $rows[$index]
  }
  $direct=@($matched | Where-Object {[int]$_.match_rank -le 2}).Count -eq $matched.Count
  $allDeclared=$hasWork -and @($sourceRows | Where-Object {
    ([string]$_.oeuvre_commune).Trim() -and ([string]$_.edition_declaree).Trim()
  }).Count -eq $sourceRows.Count
  $baseNames=@($sourceRows | ForEach-Object {
    if ($hasWork) {([string]$_.oeuvre_commune).Trim().ToLowerInvariant()} else {""}
  } | Select-Object -Unique)
  $editionNames=@($sourceRows | ForEach-Object {
    if ($hasWork) {([string]$_.edition_declaree).Trim().ToLowerInvariant()} else {""}
  } | Select-Object -Unique)
  $sourceNames=@($sourceRows | ForEach-Object {$_.serie} | Select-Object -Unique)
  if ($direct -and $allDeclared -and $baseNames.Count -eq 1 -and
      $editionNames.Count -eq $matched.Count -and
      $sourceNames.Count -eq $matched.Count) {
    $editionGroups+= [pscustomobject]@{
      manga_id=$group.Name
      oeuvre_commune=$sourceRows[0].oeuvre_commune
      editions=@($sourceRows | ForEach-Object {
        [pscustomobject]@{
          entree=$_.serie
          edition_declaree=$_.edition_declaree
          tomes_declares=[int]$_.tomes_principaux
          statut="Edition declaree, ISBN non verifies"
        }
      })
      confirmation="Oeuvre canonique partagee, editions physiques distinctes"
    }
  } else {
    $collisions+= [pscustomobject]@{
      manga_id=$group.Name
      titles=@($sourceRows | ForEach-Object {$_.serie})
      count=$matched.Count
      note="Correspondance ambiguë : editions insuffisamment verifiees"
    }
  }
}
$collisionIds=@{}
foreach($entry in $collisions) {$collisionIds[[string]$entry.manga_id]=$true}
$trusted=@{}
foreach($entry in $exact) {
  if (-not $collisionIds.ContainsKey([string]$entry.matched_manga_id)) {
    $trusted[[string]$entry.matched_manga_id]=$true
  }
}
$requests=@(
  @{name="action";text="Je veux un manga action et aventure"},
  @{name="mystere";text="Je veux un manga de mystere"},
  @{name="surprise";text="Surprends-moi selon mes gouts"}
)
$scenarios=@()
foreach($scenario in $requests) {
  $query=@{message=$scenario.text;lang="fr";limit=12;context=@{
    use_library=$true;recommendation_balance="CLOSE"
  }} | ConvertTo-Json -Depth 7 -Compress
  $result=Invoke-RestMethod -Method Post -Uri "$api/advisor/message" -TimeoutSec 60 -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($query))
  $recommendations=@($result.recommendations | ForEach-Object {
    [pscustomobject]@{id=$_.id;title=$_.title}
  })
  $owned=@($recommendations | Where-Object {$trusted.ContainsKey([string]$_.id)})
  $scenarios+= [pscustomobject]@{
    name=$scenario.name
    status=$result.status
    count=$result.count
    recommendations=$recommendations
    owned_matches_from_file=$owned
    diagnostic=$result.quality_diagnostic
    feedback=$result.feedback_learning
  }
}
if (-not (Test-Path -LiteralPath $privateDir)) {
  New-Item -Path $privateDir -ItemType Directory -Force | Out-Null
}
$previousFile=Get-ChildItem -LiteralPath $privateDir -Filter "benchmark_mangatheque_*.json" -File |
  Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
$comparison=@()
if ($null -ne $previousFile) {
  $previous=Get-Content -LiteralPath $previousFile.FullName -Encoding UTF8 -Raw | ConvertFrom-Json
  foreach($scenario in $scenarios) {
    $old=@($previous.scenarios | Where-Object {$_.name -eq $scenario.name})
    if (-not $old.Count) {continue}
    $oldIds=@($old[0].recommendations | ForEach-Object {[string]$_.id})
    $newIds=@($scenario.recommendations | ForEach-Object {[string]$_.id})
    $comparison+= [pscustomobject]@{
      scenario=$scenario.name
      previous_count=$oldIds.Count
      current_count=$newIds.Count
      unchanged_count=@($newIds | Where-Object {$_ -in $oldIds}).Count
      new_suggestion_count=@($newIds | Where-Object {$_ -notin $oldIds}).Count
      compared_to=$previousFile.Name
    }
  }
}
$report=[ordered]@{
  type="private_read_only_library_benchmark"
  created_at=(Get-Date).ToUniversalTime().ToString("o")
  source_sha256=(Get-FileHash -LiteralPath $CsvFile -Algorithm SHA256).Hash.ToLowerInvariant()
  entries=$rows.Count
  main_volumes=$totals.main
  duplicate_volumes=$totals.duplicates
  other_editions=$totals.other
  estimated_total=$totals.main+$totals.duplicates+$totals.other
  database=$health.database
  dry_run_status=$preview.status
  matched_count=$matches.Count
  direct_match_count=$exact.Count
  fuzzy_match_count=$fuzzy.Count
  missing=@($preview.not_found_items)
  errors=@($preview.error_items)
  fuzzy=@($fuzzy | ForEach-Object {
    [pscustomobject]@{input_title=$_.requested_title;catalog_title=$_.matched_title;rank=$_.match_rank}
  })
  collisions=$collisions
  groupes_editions_distinctes=$editionGroups
  trusted_canonical_match_count=$trusted.Count
  scenarios=$scenarios
  comparison_with_previous=$comparison
  limitations=@(
    "READ ONLY: aucune modification de la base.",
    "La bibliotheque actuellement en base peut differer de la liste extraite.",
    "Le fichier ne contient ni note ni lectures reelles, seulement des quantites physiques estimees.",
    "Correspondances floues, oeuvres en double et editions sans ISBN a confirmer manuellement.",
    "Seules de veritables reactions utilisateur donnent du sens a une comparaison avant/apres."
  )
}
$dest=Join-Path $privateDir ("benchmark_mangatheque_{0}_{1}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"),([guid]::NewGuid().ToString("N")).Substring(0,6))
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $dest -Encoding UTF8
Write-Host "INVENTAIRE: $($rows.Count) entrees, $($totals.main) principaux, $($totals.duplicates) doublons, $($totals.other) autres editions."
Write-Host "MATCHS: $($matches.Count) identifiables, $($exact.Count) directs, $($fuzzy.Count) flous, $(@($preview.not_found_items).Count) absents, $($collisions.Count) collisions ambigues."
Write-Host "EDITIONS: $($editionGroups.Count) groupe(s) de versions physiques distinctes d'une meme oeuvre (ISBN non verifies)."
foreach($scenario in $scenarios) {
  Write-Host "CONSEILLER $($scenario.name): $($scenario.count) propositions, $(@($scenario.owned_matches_from_file).Count) recoupement(s) sur titres relies avec certitude."
}
foreach($item in $comparison) {
  Write-Host "EVOLUTION $($item.scenario): $($item.new_suggestion_count) nouvelles propositions depuis le test precedent."
}
Write-Host "Rapport local prive: $dest"
Write-Host "AUCUNE DONNEE IMPORTÉE OU MODIFIÉE."
