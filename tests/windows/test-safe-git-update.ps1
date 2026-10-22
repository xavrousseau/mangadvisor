# Exercise the REAL update function in a disposable Windows Git clone.
# Docker and PostgreSQL are mocked; no personal user data is accessed.
$ErrorActionPreference = "Stop"
$base=Join-Path $env:RUNNER_TEMP "ma_git_update_ci"
New-Item -ItemType Directory -Force -Path $base | Out-Null
$seed=Join-Path $base "seed"
$remote=Join-Path $base "remote.git"
$working=Join-Path $base "working"
& git init --initial-branch=main $seed | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Git init failed" }
& git -C $seed config user.email "mangadvisor-ci@example.invalid"
& git -C $seed config user.name "Mangadvisor CI"
[IO.File]::WriteAllText((Join-Path $seed "README.txt"),("v1"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
New-Item -ItemType Directory -Path (Join-Path $seed "cmd") -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $seed "cmd\library-backup.ps1"),"function Prepare-Existing-Postgres { }",(New-Object Text.UTF8Encoding($false)))
Copy-Item (Join-Path $PWD ".gitignore") (Join-Path $seed ".gitignore")
Copy-Item (Join-Path $PWD ".gitattributes") (Join-Path $seed ".gitattributes")
& git -C $seed add README.txt .gitignore .gitattributes cmd/library-backup.ps1
& git -C $seed commit -m initial | Out-Null
if ($LASTEXITCODE -ne 0) { throw "First commit failed" }
& git init --bare --initial-branch=main $remote | Out-Null
& git -C $seed remote add origin $remote
& git -C $seed push -u origin main | Out-Null
if ($LASTEXITCODE -ne 0) { throw "First push failed" }
& git clone $remote $working | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Clone failed" }
& git -C $working config user.email "mangadvisor-ci@example.invalid"
& git -C $working config user.name "Mangadvisor CI"
& git -C $working config core.autocrlf true

# The full update now delegates safe untracked-collision handling to a
# dedicated script. Install that script in this disposable clone as the
# real repository would provide it, without modifying the remote fixture.
New-Item -ItemType Directory -Force -Path (Join-Path $working "cmd") | Out-Null
Copy-Item -LiteralPath (Join-Path $PWD "cmd/github-sync.ps1") -Destination (Join-Path $working "cmd/github-sync.ps1")

# Remote update pending while local tracked README is different.
[IO.File]::WriteAllText((Join-Path $seed "README.txt"),("v2"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
& git -C $seed add README.txt
& git -C $seed commit -m remote-update | Out-Null
& git -C $seed push origin main | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Remote push failed" }
[IO.File]::WriteAllText((Join-Path $working "README.txt"),("My valuable local changes"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
[IO.File]::WriteAllText((Join-Path $working ".env"),("POSTGRES_PASSWORD=LOCAL_TEST_DO_NOT_STASH"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
New-Item -ItemType Directory -Path (Join-Path $working "private-data") | Out-Null
[IO.File]::WriteAllText((Join-Path (Join-Path $working "private-data") "my-manga.csv"),("PRIVATE_INVENTORY_TEST"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))

# Read real Update. Mock Docker/SQL and validate PostgreSQL backup order.
. (Join-Path $PWD "cmd/control-center.ps1") -Action Environment
$script:root=$working
$script:backupCalls=0
function Ensure-Environment {}
function Check-Docker {}
function Initialize-Database {}
function Start-Application {}
function Diagnostic {}
function Backup {
  $script:backupCalls++
  $changes=@(& git -C $script:root status --porcelain=v1 --untracked-files=no)
  if ($changes.Count -eq 0) { throw "Backup must precede Git stash" }
}
function Confirm([string]$Question,[bool]$Default=$false) { return $true }

Update
if ($script:backupCalls -ne 1) { throw "Database backup not called exactly once" }
$head=(& git -C $working rev-parse HEAD).Trim()
$expected=(& git -C $remote rev-parse refs/heads/main).Trim()
if ($head -cne $expected) { throw "Pull did not fast-forward to remote main" }
$stash=@(& git -C $working stash list --format="%gs")
if ($stash.Count -ne 1 -or $stash[0] -notlike "*mangadvisor-avant-maj-*") {
  throw "Original changes not saved in named stash"
}
$stashDiff=(& git -C $working stash show -p "stash@{0}") -join [Environment]::NewLine
if ($stashDiff -notmatch "valuable local changes") {
  throw "Original source modifications were not preserved"
}
if ((Get-Content (Join-Path $working ".env") -Raw) -notmatch "LOCAL_TEST_DO_NOT_STASH") {
  throw "Private .env was changed"
}
if (!(Test-Path (Join-Path $working "private-data/my-manga.csv"))) {
  throw "Private library was changed"
}
if ((Get-Content (Join-Path $working "README.txt") -Raw) -notmatch "v2") {
  throw "Remote code was not deployed"
}

# A declined prompt must leave tracked files and the existing stash alone.
[IO.File]::WriteAllText((Join-Path $working "README.txt"),("Local edits that must stay"+[Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))
$script:backupCalls=0
function Confirm([string]$Question,[bool]$Default=$false) { return $false }
$refused=$false
try { Update } catch {
  $refused=$true
  if ($_.Exception.Message -notmatch "annulee") { throw }
}
if (-not $refused) { throw "User refusal must cancel update" }
if ($script:backupCalls -ne 0) { throw "No database backup when user cancels" }
if ((Get-Content (Join-Path $working "README.txt") -Raw) -notmatch "must stay") {
  throw "Cancelled update changed a tracked file"
}
if (@(& git -C $working stash list --format="%gs").Count -ne 1) {
  throw "Cancelled update modified stash"
}
Write-Host "OK: real local stash, fast-forward, pre-stash backup, private files and user refusal."
