# Reproduce the full public-catalogue export with a Docker shim.
# Must run under Windows PowerShell 5.1; never starts Docker or reads real data.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script:dumpArguments=@()
$script:dockerCallCount=0
$script:sourceTables=@("manga","manga_title_alias","manga_bnf_candidate","jikan_manga_source")

function docker {
  $call=@($args)
  $script:dockerCallCount++
  $global:LASTEXITCODE=0
  if ($call.Count -lt 1) { throw "Empty Docker command" }
  if ($call[0] -eq "container" -and $call[1] -eq "inspect") {
    return '{"com.docker.compose.project":"mangadvisor","com.docker.compose.service":"postgres"}'
  }
  if ($call[0] -eq "inspect") {
    if ($call -contains '{{.State.Running}}') { return "true" }
    if ($call -contains '{{range .Config.Env}}{{println .}}{{end}}') {
      return "POSTGRES_DB=mangadvisor","POSTGRES_USER=mangadvisor","POSTGRES_PASSWORD=NOT_EXPORTED"
    }
    throw "Unknown Docker inspect invocation"
  }
  if ($call[0] -eq "cp") {
    $target=[string]$call[$call.Count-1]
    [IO.File]::WriteAllBytes($target,[byte[]](80,71,68,77,80,1,2,3))
    return
  }
  if ($call[0] -ne "exec") { throw "Unexpected Docker command: $($call[0])" }
  if ($call.Count -lt 3 -or $call[1] -cne "mangadvisor_postgres") {
    throw "Export used the wrong container"
  }
  if ($call[2] -eq "psql") {
    $statement=[string]$call[$call.Count-1]
    if ($statement -match "FROM pg_tables") {
      return $script:sourceTables
    }
    if ($statement -match "^SELECT count\(") {
      return "103"
    }
    throw "Unexpected SQL during read-only export"
  }
  if ($call[2] -eq "pg_dump") {
    # Insist on one atomic table argument per allowed public table.
    $script:dumpArguments+= ,$call
    $tableArgs=@($call | Where-Object { ([string]$_).StartsWith("--table=", [StringComparison]::Ordinal) })
    foreach ($arg in $tableArgs) {
      if ($arg -notmatch '^--table=public\.[a-z_]+$') {
        throw "Invalid native pg_dump table selector: $arg"
      }
    }
    if ($call -contains "manga" -or $call -contains "manga_title_alias" -or
        $call -contains "public." -or $call -contains "-t") {
      throw "Broken PowerShell table arguments: $($call -join ' | ')"
    }
    foreach ($expected in @("--table=public.manga",
                            "--table=public.manga_title_alias",
                            "--table=public.manga_bnf_candidate")) {
      if ($tableArgs -notcontains $expected) {
        throw "Missing table selector $expected"
      }
    }
    if ($tableArgs.Count -ne 3) {
      throw "Expected three public metadata table selectors, got $($tableArgs.Count)"
    }
    return
  }
  if ($call[2] -eq "pg_restore") { return "Archive TOC" }
  if ($call[2] -eq "rm") { return }
  throw "Unmocked docker exec: $($call -join ' | ')"
}

try {
  # Dot-source to make the mocked Docker function available inside the real
  # script; -SkipRaw intentionally avoids a second archive in this test.
  . (Join-Path $root "cmd\export-catalogue-public.ps1") -SkipRaw
  if ($script:dumpArguments.Count -ne 1) {
    throw "Expected a single pg_dump invocation"
  }
  if (!(Test-Path -LiteralPath $manifestPath)) { throw "Missing manifest" }
  $report=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
  if ($report.includes_personal_library -ne $false -or
      $report.includes_passwords -ne $false) {
    throw "Export privacy flags are incorrect"
  }
  if (@($report.archives).Count -ne 1 -or
      @($report.records).Count -ne 4) {
    throw "Unexpected number of public archive records"
  }
  if ((@($report.quality_indicators) | Where-Object {
    $_.metric -eq "bnf_isbn_candidate_count"
  }).Count -ne 1) { throw "Catalogue global metrics are absent" }
  Write-Host "PASS: full public metadata export uses atomic pg_dump --table args on PowerShell 5.1"
} finally {
  # Only remove the files created by this synthetic test.
  if ((Test-Path variable:exportName) -and
      $exportName -match '^catalogue_[0-9]{8}_[0-9]{6}_[a-f0-9]{8}$') {
    foreach ($file in @(
      (Join-Path $root ("backups\catalogue-public\" + $exportName + "_metadata.dump")),
      (Join-Path $root ("backups\catalogue-public\" + $exportName + "_manifest.json"))
    )) {
      if (Test-Path -LiteralPath $file) {
        Remove-Item -LiteralPath $file -Force
      }
    }
  }
}
