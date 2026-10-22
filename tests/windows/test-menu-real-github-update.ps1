# End-to-end Windows check of menu 7 while it updates its own batch file.
# Uses disposable local Git repositories only. Never touches Docker.
$ErrorActionPreference="Stop"
$base=Join-Path $env:RUNNER_TEMP ("ma_menu_sync_"+[guid]::NewGuid().ToString("N").Substring(0,8))
$seed=Join-Path $base "seed"
$remote=Join-Path $base "remote.git"
$working=Join-Path $base "working"
New-Item -ItemType Directory -Force -Path $seed | Out-Null
function Run-FixtureGit([string[]]$arguments) {
  & git @arguments | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Fixture Git failed: $($arguments -join ' ')" }
}
try {
  Run-FixtureGit @("init","--initial-branch=main",$seed)
  Run-FixtureGit @("-C",$seed,"config","user.name","Mangadvisor CI")
  Run-FixtureGit @("-C",$seed,"config","user.email","mangadvisor-ci@example.invalid")
  New-Item -ItemType Directory -Force -Path (Join-Path $seed "cmd") | Out-Null
  Copy-Item (Join-Path $PWD "mangadvisor.cmd") (Join-Path $seed "mangadvisor.cmd")
  Copy-Item (Join-Path $PWD "cmd\github-sync.ps1") (Join-Path $seed "cmd\github-sync.ps1")
  [IO.File]::WriteAllText((Join-Path $seed "cmd\library-backup.ps1"),
    "function Prepare-Existing-Postgres { }"+[Environment]::NewLine,[Text.Encoding]::ASCII)
  Run-FixtureGit @("-C",$seed,"add",".")
  Run-FixtureGit @("-C",$seed,"commit","-m","initial")
  Run-FixtureGit @("init","--bare","--initial-branch=main",$remote)
  Run-FixtureGit @("-C",$seed,"remote","add","origin",$remote)
  Run-FixtureGit @("-C",$seed,"push","-u","origin","main")
  Run-FixtureGit @("clone",$remote,$working)

  [IO.File]::AppendAllText((Join-Path $seed "mangadvisor.cmd"),
    [Environment]::NewLine+"rem CI_MENU_SELF_UPDATE_SUCCESS"+[Environment]::NewLine,[Text.Encoding]::ASCII)
  [IO.File]::AppendAllText((Join-Path $seed "cmd\library-backup.ps1"),
    "rem REMOTE_BACKUP_SCRIPT"+[Environment]::NewLine,[Text.Encoding]::ASCII)
  Run-FixtureGit @("-C",$seed,"add",".")
  Run-FixtureGit @("-C",$seed,"commit","-m","new release modifies running batch file")
  Run-FixtureGit @("-C",$seed,"push","origin","main")
  $expected=(& git -C $remote rev-parse refs/heads/main).Trim()

  $stdin=Join-Path $base "stdin.txt"
  $stdout=Join-Path $base "stdout.txt"
  $stderr=Join-Path $base "stderr.txt"
  $inputLines=(@("7","","0","0","0","0","0","0") -join [Environment]::NewLine)+[Environment]::NewLine
  [IO.File]::WriteAllText($stdin,$inputLines,[Text.Encoding]::ASCII)
  $proc=Start-Process -FilePath "cmd.exe" -ArgumentList @("/d","/c","mangadvisor.cmd") -WorkingDirectory $working -RedirectStandardInput $stdin -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
  if (-not $proc.WaitForExit(25000)) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw "Menu 7 hangs while replacing its own batch file."
  }
  $out=[IO.File]::ReadAllText($stdout)+[IO.File]::ReadAllText($stderr)
  if ($out -notmatch "Code ET script de sauvegarde verifies") {
    throw "Menu 7 did not report verified code. Output: $out"
  }
  $actual=(& git -C $working rev-parse HEAD).Trim()
  if ($actual -cne $expected) { throw "Menu 7 did not install remote commit." }
  if (-not ([IO.File]::ReadAllText((Join-Path $working "mangadvisor.cmd"))).Contains("CI_MENU_SELF_UPDATE_SUCCESS")) {
    throw "Running batch was not updated."
  }
  if (-not ([IO.File]::ReadAllText((Join-Path $working "cmd\library-backup.ps1"))).Contains("REMOTE_BACKUP_SCRIPT")) {
    throw "The backup script stayed stale."
  }
  Write-Host "OK: menu 7 changed its running batch file and backup script, SHA matched."
} finally {
  Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction SilentlyContinue
}
