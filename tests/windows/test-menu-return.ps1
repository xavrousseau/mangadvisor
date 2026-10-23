# Test real interactive mangadvisor.cmd on Windows with synthetic actions.
# Nothing runs against production Docker, Git or user data.
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$fixture=Join-Path $env:RUNNER_TEMP ("ma_menu_loop_"+[guid]::NewGuid().ToString("N").Substring(0,8))
$actionDir=Join-Path $fixture "cmd"
New-Item -ItemType Directory -Path $actionDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PWD "mangadvisor.cmd") -Destination (Join-Path $fixture "mangadvisor.cmd")
$stub=@'
param([string]$Action)
Write-Output ("MA_FIXTURE_ACTION_"+$Action)
if ($Action -eq "Inventory") { exit 37 }
exit 0
'@
[IO.File]::WriteAllText((Join-Path $actionDir "control-center.ps1"),$stub,[Text.Encoding]::ASCII)
$stub2=@'
Write-Output "MA_FIXTURE_SYNC_FINISHED"
exit 0
'@
[IO.File]::WriteAllText((Join-Path $actionDir "github-sync.ps1"),$stub2,[Text.Encoding]::ASCII)

function Check-Menu([string]$Name, [string]$InputText,
                    [string]$Marker, [string]$SecondMenu, [bool]$ExpectFailure) {
    $inputFile=Join-Path $fixture ("stdin_"+$Name+".txt")
    $stdoutFile=Join-Path $fixture ("stdout_"+$Name+".txt")
    $stderrFile=Join-Path $fixture ("stderr_"+$Name+".txt")
    [IO.File]::WriteAllText($inputFile,$InputText,[Text.Encoding]::ASCII)
    $p=Start-Process -FilePath "cmd.exe" -ArgumentList @("/d","/c","mangadvisor.cmd") -WorkingDirectory $fixture -RedirectStandardInput $inputFile -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile -PassThru
    if (!$p.WaitForExit(13000)) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        throw "$Name : le menu est bloque; sortie partielle dans $stdoutFile"
    }
    $output=[IO.File]::ReadAllText($stdoutFile)+[IO.File]::ReadAllText($stderrFile)
    # A redirected file cannot behave exactly like a keyboard at the
    # subsequent PAUSE and may exhaust stdin after the menu is shown again.
    # Check the durable guarantee: the result appeared and the menu returned.
    # Separate Windows CI tests cover clean zero-exit navigation with no action.
    if (!$output.Contains($Marker)) {
        throw "$Name : l'action fictive n'a pas ete executee. $output"
    }
    $occurrences=[regex]::Matches($output,[regex]::Escape($SecondMenu)).Count
    if ($occurrences -lt 2) {
        throw "$Name : le menu ne revient PAS apres le traitement ($occurrences affichage(s)). $output"
    }
    if ($ExpectFailure -and !$output.Contains("ECHEC - code 37.")) {
        throw "$Name : le code de retour 37 doit etre affiche sans fermer la console. $output"
    }
    if (!$ExpectFailure -and !$output.Contains("Operation terminee.")) {
        throw "$Name : le resultat n'est pas affiche. $output"
    }
    Write-Host ("OK : " + $Name + " renvoie au menu avec le resultat visible.")
}

$crlf=([string][char]13)+([string][char]10)
# Extra zero lines tolerate how cmd.exe reads redirected pause / set /p.
Check-Menu "catalogue_lifecycle" ((@("A","1","1","","0","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_CatalogueLifecycle" "CATALOGUE ET RECHERCHE" $false
Check-Menu "search_index" ((@("A","1","2","","0","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_SearchIndex" "CATALOGUE ET RECHERCHE" $false
Check-Menu "import_failure" ((@("A","2","1","","0","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_Inventory" "MA BIBLIOTHEQUE" $true
Check-Menu "recommendations" ((@("A","3","5","","0","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_Recommendations" "FONCTIONS FACULTATIVES" $false
Check-Menu "maintenance_status" ((@("A","S","1","","0","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_Status" "ENTRETIEN ET SECOURS" $false
Check-Menu "github_sync" ((@("7","","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_SYNC_FINISHED" "MANGADVISOR" $false
Check-Menu "normal_update" ((@("3","","0","0","0") -join $crlf)+$crlf) "MA_FIXTURE_ACTION_Update" "MANGADVISOR" $false
Write-Host "Tests de retours interactifs Windows reussis sans Git ni Docker."
