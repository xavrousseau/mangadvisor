# Test the REAL GitHub sync script against an isolated local bare Git remote.
# No Docker, user data, or GitHub access is used for this test.
$ErrorActionPreference="Stop"
$base=Join-Path $env:RUNNER_TEMP ("ma_sync_ci_" + [guid]::NewGuid().ToString("N").Substring(0,8))
$seed=Join-Path $base "seed"
$remote=Join-Path $base "remote.git"
$working=Join-Path $base "working"
$sync=Join-Path $PWD "cmd\github-sync.ps1"
New-Item -ItemType Directory -Force -Path $base | Out-Null

function Git([string[]]$Commands) {
  & git @Commands | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Git command failed: $($Commands -join ' ')" }
}
function Write-Text([string]$File,[string]$Value) {
  $parent=Split-Path -Parent $File
  if (!(Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  [IO.File]::WriteAllText($File,$Value,(New-Object Text.UTF8Encoding($false)))
}

Git @("init","--initial-branch=main",$seed)
Git @("-C",$seed,"config","user.email","mangadvisor-ci@example.invalid")
Git @("-C",$seed,"config","user.name","Mangadvisor CI")
Copy-Item (Join-Path $PWD ".gitignore") (Join-Path $seed ".gitignore")
Write-Text (Join-Path $seed "README.txt") "old code"
Git @("-C",$seed,"add",".")
Git @("-C",$seed,"commit","-m","initial")
Git @("init","--bare","--initial-branch=main",$remote)
Git @("-C",$seed,"remote","add","origin",$remote)
Git @("-C",$seed,"push","-u","origin","main")
Git @("clone",$remote,$working)
Git @("-C",$working,"config","user.email","mangadvisor-ci@example.invalid")
Git @("-C",$working,"config","user.name","Mangadvisor CI")

# Exactly the kind of collision experienced by the user: a manually copied
# file that was untracked before it became an official upstream tracked file.
$conflicts=@("apps/api/app/bnf_batch.py",
             "tests/test_bnf_batch.py",
             "cmd/github-sync.ps1")
foreach ($name in $conflicts) {
  Write-Text (Join-Path $working $name) ("LOCAL VERSION " + $name)
  Write-Text (Join-Path $seed $name) ("OFFICIAL VERSION " + $name)
}
Write-Text (Join-Path $working ".env") "LOCAL CONFIGURATION SECRET"
Write-Text (Join-Path $working "private-data\mangatheque.csv") "PRIVATE MANGA LIBRARY"
Write-Text (Join-Path $working "backups\existing.dump") "PRIVATE BACKUP"
Write-Text (Join-Path $working "data\raw\original.json") "CACHED CATALOG"
Write-Text (Join-Path $working "notes-perso.txt") "UNRELATED UNTRACKED WORK"
Write-Text (Join-Path $seed "README.txt") "new code"
Git @("-C",$seed,"add",".")
Git @("-C",$seed,"commit","-m","new version")
Git @("-C",$seed,"push","origin","main")

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync -Root $working -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Safe GitHub sync failed despite recoverable collisions." }

$head=(& git -C $working rev-parse HEAD).Trim()
$expected=(& git -C $remote rev-parse refs/heads/main).Trim()
if ($head -cne $expected) { throw "Sync did not update main." }
foreach ($name in $conflicts) {
  $newFile=Get-Content -LiteralPath (Join-Path $working $name) -Raw
  if ($newFile -cne ("OFFICIAL VERSION " + $name)) { throw "Official code not installed: $name" }
}
$archives=@(Get-ChildItem (Join-Path $base "mangadvisor-archives-git") -Directory)
if ($archives.Count -ne 1) { throw "Expected one unique external archive." }
foreach ($name in $conflicts) {
  $file=Join-Path $archives[0].FullName $name
  if (!(Test-Path -LiteralPath $file)) { throw "Local collision not archived: $name" }
  if ((Get-Content -LiteralPath $file -Raw) -cne ("LOCAL VERSION " + $name)) {
    throw "Archived content differs: $name"
  }
}
foreach ($entry in @(
  @(".env","LOCAL CONFIGURATION SECRET"),
  @("private-data\mangatheque.csv","PRIVATE MANGA LIBRARY"),
  @("backups\existing.dump","PRIVATE BACKUP"),
  @("data\raw\original.json","CACHED CATALOG"),
  @("notes-perso.txt","UNRELATED UNTRACKED WORK")
)) {
  if ((Get-Content -LiteralPath (Join-Path $working $entry[0]) -Raw) -cne $entry[1]) {
    throw "Unrelated user file changed: $($entry[0])"
  }
}
$stash=@(& git -C $working stash list --format="%gs")
if ($stash.Count -ne 0) { throw "Unexpected stash during a clean collision-only update." }
if (@(& git -C $working status --porcelain=v1 --untracked-files=no).Count -ne 0) {
  throw "Tracked files must be clean after sync."
}

# Second run must be idempotent and not create backup copies again.
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync -Root $working -NonInteractive
if ($LASTEXITCODE -ne 0) { throw "Idempotent rerun failed." }
if (@(Get-ChildItem (Join-Path $base "mangadvisor-archives-git") -Directory).Count -ne 1) {
  throw "Second run created a redundant archive."
}

# Local tracked changes require consent, not silent stash.
Write-Text (Join-Path $seed "README.txt") "new upstream code 3"
Git @("-C",$seed,"add","README.txt")
Git @("-C",$seed,"commit","-m","upstream-again")
Git @("-C",$seed,"push","origin","main")
Write-Text (Join-Path $working "README.txt") "LOCAL IMPORTANT MODIFICATION"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync -Root $working -NonInteractive
if ($LASTEXITCODE -eq 0) { throw "Noninteractive dirty tracked update should fail closed." }
if ((Get-Content (Join-Path $working "README.txt") -Raw) -cne "LOCAL IMPORTANT MODIFICATION") {
  throw "Tracked local modifications were overwritten."
}
if (@(& git -C $working stash list --format="%gs").Count -ne 0) {
  throw "Tracked local edits were stashed without consent."
}

# ZIP/unconnected folder cannot be silently overwritten.
$zip=Join-Path $base "zip-copy"
New-Item -ItemType Directory -Force -Path $zip | Out-Null
Write-Text (Join-Path $zip "mangadvisor.cmd") "A ZIP copy without .git"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sync -Root $zip -NonInteractive
if ($LASTEXITCODE -eq 0) { throw "Unconnected ZIP folder must be rejected safely." }
if ((Get-Content (Join-Path $zip "mangadvisor.cmd") -Raw) -cne "A ZIP copy without .git") {
  throw "ZIP contents changed despite safety stop."
}

Write-Host "OK: safe archive of colliding untracked files, exact remote code, ignored data retained, idempotence, no silent stash, ZIP protection."
