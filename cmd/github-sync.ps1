# Mangadvisor - safe GitHub code sync for Windows PowerShell 5.1.
# Only source files tracked by Git are updated; PostgreSQL and private files are not touched.
# Conflicting untracked local files are archived outside the repository, never deleted.
param(
  [string]$Root="",
  [switch]$NonInteractive
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
if (-not $Root) { $Root=Join-Path $PSScriptRoot ".." }
$repo=(Resolve-Path -LiteralPath $Root).Path
$gitDir=Join-Path $repo ".git"

function Git-Output([string[]]$Arguments,[string]$Failure) {
  $out=@(& git -C $repo @Arguments)
  if ($LASTEXITCODE -ne 0) { throw "$Failure (code $LASTEXITCODE)." }
  return $out
}

function Git-Run([string[]]$Arguments,[string]$Failure) {
  & git -C $repo @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Failure (code $LASTEXITCODE)." }
}

function Git-One([string[]]$Arguments,[string]$Failure) {
  $lines=@(Git-Output $Arguments $Failure)
  if ($lines.Count -ne 1 -or -not ([string]$lines[0]).Trim()) {
    throw "$Failure (reponse Git inattendue)."
  }
  return ([string]$lines[0]).Trim()
}

function Safe-RelativePath([string]$GitPath) {
  # Only normal files INSIDE this repository can be archived.
  $relative=$GitPath.Replace("/","\")
  if ([IO.Path]::IsPathRooted($relative) -or
      $relative -match '(^|\\)\.\.(\\|$)' -or
      $relative -match '(^|\\)\.git(\\|$)' -or
      $relative -match '^(?i:(\.env|private-data|backups|data\\raw))(\\|$)') {
    throw "Fichier local protege ou chemin suspect : $GitPath"
  }
  $absolute=[IO.Path]::GetFullPath((Join-Path $repo $relative))
  $prefix=$repo.TrimEnd('\')+'\'
  if (-not $absolute.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) {
    throw "Chemin hors du projet refuse : $GitPath"
  }
  return $relative
}

function Ask-TrackedStash {
  if ($NonInteractive) {
    throw "Des fichiers de code suivis sont modifies : mise a jour annulee sans intervention."
  }
  Write-Host ""
  Write-Host "Des fichiers de code suivis ont ete modifies localement."
  Write-Host "Je peux les sauvegarder dans un stash Git local sans les effacer."
  Write-Host "Ils ne seront pas reappliques automatiquement sur la nouvelle version."
  $choice=Read-Host "Sauvegarder ces modifications puis continuer ? (o/N)"
  if ($choice -notmatch '^(o|oui|y|yes)$') {
    throw "Mise a jour annulee a ta demande. Tes fichiers sont conserves."
  }
}

function Assert-Backup-Script {
  # A checkout can contain the expected commit but an unexpected file on
  # disk. This check catches the specific stale backup failure mode.
  $file=Join-Path $repo "cmd\library-backup.ps1"
  if (!(Test-Path -LiteralPath $file -PathType Leaf)) {
    throw "Sauvegarde Mangadvisor absente : cmd\library-backup.ps1. Code incomplet."
  }
  $source=[IO.File]::ReadAllText($file,[Text.Encoding]::UTF8)
  if (-not $source.Contains("function Prepare-Existing-Postgres")) {
    throw "Le script de sauvegarde est obsolete : impossible d'annoncer le code a jour. Ne pas relancer le menu 3."
  }
}

function Sync-GitHub {
  Write-Host ""
  Write-Host "=== Mangadvisor : recuperer le code depuis GitHub ==="
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git pour Windows n'est pas installe. Installe-le depuis https://git-scm.com/downloads/win."
  }
  if (-not (Test-Path -LiteralPath $gitDir)) {
    throw "Ce dossier n'est pas un clone Git. Aucun fichier n'a ete remplace. Il faut d'abord cloner le depot officiel dans un dossier vide."
  }
  $top=Git-One @("rev-parse","--show-toplevel") "Depot Git illisible"
  if ([IO.Path]::GetFullPath($top).TrimEnd('\') -ine $repo.TrimEnd('\')) {
    throw "Ce lanceur doit etre execute depuis la racine du depot Mangadvisor."
  }
  $branch=Git-One @("branch","--show-current") "Branche Git inconnue"
  if ($branch -cne "main") {
    throw "Branche actuelle : $branch. Mise a jour reservee a main pour eviter les pertes."
  }
  $remote=Git-One @("remote","get-url","origin") "Depot distant origin introuvable"
  Write-Host "Source du code : $remote"
  Write-Host "Recherche de la version main la plus recente..."
  Git-Run @("fetch","--no-tags","origin","main") "Telechargement GitHub impossible"

  $current=Git-One @("rev-parse","HEAD") "Commit local inconnu"
  $target=Git-One @("rev-parse","FETCH_HEAD") "Commit distant inconnu"
  Write-Host ("Version avant synchronisation : " + $current.Substring(0,12))
  Write-Host ("Version GitHub disponible   : " + $target.Substring(0,12))
  if ($current -cne $target) {
    & git -C $repo merge-base --is-ancestor HEAD FETCH_HEAD
    if ($LASTEXITCODE -eq 1) {
      throw "Historiques Git divergents. Aucun fichier n'a ete change. Ne pas forcer un reset : conserver l'ancien dossier et demander une migration."
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Impossible de verifier que la mise a jour est sans risque."
    }
  }

  # IMPORTANT: even when HEAD == FETCH_HEAD, tracked files can contain
  # staged/unstaged edits (including an old copy of library-backup.ps1).
  # Never report an installation as up to date without checking its files.
  # Preserve tracked edits explicitly, never touching untracked/private paths.
  $changes=@(Git-Output @("status","--porcelain=v1","--untracked-files=no") "Lecture des fichiers locaux impossible")
  if ($changes.Count -gt 0) {
    Write-Host ("Fichiers suivis modifies : {0}" -f $changes.Count)
    $changes | Select-Object -First 15 | ForEach-Object { Write-Host ("  " + $_) }
    Ask-TrackedStash
    $label="mangadvisor-code-local-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Git-Run @("stash","push","-m",$label) "Sauvegarde Git des modifications locales impossible"
    $after=@(Git-Output @("status","--porcelain=v1","--untracked-files=no") "Verification stash impossible")
    if ($after.Count -gt 0) {
      throw "Le code suivi est encore modifie. Mise a jour interrompue."
    }
    Write-Host "Code local suivi preserve : git stash list"
  }

  if ($current -ceq $target) {
    $clean=@(Git-Output @("status","--porcelain=v1","--untracked-files=no") "Verification de la version deja installee impossible")
    if ($clean.Count -gt 0) {
      throw "Le code suivi reste modifie apres la sauvegarde. Ne pas annoncer une mise a jour reussie."
    }
    Assert-Backup-Script
    Write-Host "Code et scripts de sauvegarde deja au niveau de GitHub : $($current.Substring(0,12))."
    Write-Host "Aucun changement des donnees Docker, du fichier .env ou des fichiers personnels."
    return
  }

  # Git refuses to fast-forward when untracked local files have names that
  # are now tracked upstream. Find only those exact conflicts, not every local
  # untracked file. In particular, never touch ignored user data.
  $upstream=@(Git-Output @("-c","core.quotePath=false","ls-tree","-r","--name-only","FETCH_HEAD") "Liste des fichiers GitHub impossible")
  $upstreamNames=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($name in $upstream) {
    if ($name) { $null=$upstreamNames.Add(([string]$name)) }
  }
  $untracked=@(Git-Output @("-c","core.quotePath=false","ls-files","--others","--exclude-standard") "Liste des fichiers locaux impossible")
  $conflicts=New-Object 'System.Collections.Generic.List[string]'
  foreach ($name in $untracked) {
    $value=[string]$name
    if ($upstreamNames.Contains($value)) { $conflicts.Add($value) }
  }

  if ($conflicts.Count -gt 0) {
    $parent=Split-Path -Parent $repo
    $archive=Join-Path $parent ("mangadvisor-archives-git\" +
      (Get-Date -Format 'yyyyMMdd_HHmmss') + "_" + [guid]::NewGuid().ToString("N").Substring(0,8))
    # Validate all source paths before moving a single file.
    $moves=@()
    foreach ($name in $conflicts) {
      $relative=Safe-RelativePath $name
      $source=Join-Path $repo $relative
      if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Fichier de conflit introuvable : $source"
      }
      if ((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Lien symbolique local refuse : $source"
      }
      $moves+=@([pscustomobject]@{ Rel=$relative; Src=$source; Dst=(Join-Path $archive $relative) })
    }
    Write-Host ("{0} fichier(s) locaux genants : archivage automatique sans suppression." -f $moves.Count)
    Write-Host "Dossier de sauvegarde : $archive"
    foreach ($move in $moves) {
      $directory=Split-Path -Parent $move.Dst
      if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
      }
      Move-Item -LiteralPath $move.Src -Destination $move.Dst -ErrorAction Stop
      Write-Host ("  Sauvegarde : " + $move.Rel)
    }
  }

  # No reset, no clean, no -v, no database modifications.
  Git-Run @("merge","--ff-only","FETCH_HEAD") "Mise a jour Git impossible"
  $updated=Git-One @("rev-parse","HEAD") "Verification finale impossible"
  if ($updated -cne $target) {
    throw "La version apres mise a jour ne correspond pas au commit distant."
  }
  $remaining=@(Git-Output @("status","--porcelain=v1","--untracked-files=no") "Verification des fichiers suivis impossible")
  if ($remaining.Count -ne 0) {
    throw "Mise a jour terminee mais des fichiers de code restent modifies : ne pas lancer l'option 3."
  }
  Assert-Backup-Script
  Write-Host ""
  Write-Host ("Code ET script de sauvegarde verifies : " + $updated.Substring(0,12))
  Write-Host "Les fichiers prives (.env, private-data, backups) et Docker sont preserves."
  Write-Host "Utilise l'option 3 pour reconstruire les conteneurs si necessaire."
}

try {
  Sync-GitHub
  exit 0
} catch {
  Write-Host ""
  Write-Host ("ECHEC : " + $_.Exception.Message) -ForegroundColor Red
  Write-Host "Aucun git reset --hard, git clean ou effacement Docker n'a ete lance."
  exit 1
}
