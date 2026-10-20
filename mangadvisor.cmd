@echo off
setlocal

set "ROOT_DIR=%~dp0"

if not "%~1"=="" goto run_command

:menu
cls
echo ============================================================
echo                        MANGADVISOR CLI
echo ============================================================
echo.
echo   Stack Docker
echo   ------------
echo   1  - Verification de l'installation
echo   2  - Build des images
echo   3  - Build + demarrage
echo   4  - Demarrage
echo   5  - Etat des services
echo   6  - Logs
echo   7  - Stop
echo   8  - Down
echo   9  - Restart
echo   10 - Clean
echo   11 - Nuke
echo.
echo   Extensions optionnelles
echo   ----------------------
echo   13 - Activer le scanner mobile HTTPS
echo   14 - Arreter le scanner mobile HTTPS
echo   15 - Installer et activer le conseiller IA local
echo   16 - Arreter le conseiller IA local
echo.
echo   Sauvegarde de la mangatheque
echo   ---------------------------
echo   17 - Sauvegarder et verifier
echo   18 - Verifier la derniere sauvegarde
echo   19 - Restaurer (confirmation obligatoire)
echo   20 - Tester ma mangatheque en lecture seule
echo   21 - Importer ma mangatheque apres verification
echo.
echo.
echo   Centre de pilotage - Installation et donnees
echo   -----------------------------------------
echo   22 - Installer de A a Z (base, donnees, appli, bibliotheque, tests)
echo   23 - Creer / verifier la configuration .env
echo   24 - Initialiser / reparer les tables SQL
echo   25 - Telecharger et charger le catalogue manga (Tenrai)
echo   26 - Telecharger et charger les recommandations
echo   27 - Diagnostic final complet (lecture seule)
echo   28 - Mise a jour securisee (sauvegarde + Git + Docker)
echo   29 - Diagnostic reseau Docker / API manga
echo   Q  - Quitter
echo.
echo ============================================================
echo Exemples de commandes directes :
echo   mangadvisor.cmd check
echo   mangadvisor.cmd build
echo   mangadvisor.cmd start
echo   mangadvisor.cmd logs
echo   mangadvisor.cmd catalogue
echo ============================================================
echo.

set /p CHOICE=Votre choix : 

if /I "%CHOICE%"=="1" (
    start "Mangadvisor - Verification" cmd /k call "%ROOT_DIR%cmd\install-check.cmd"
    goto menu
)
if /I "%CHOICE%"=="2" (
    start "Mangadvisor - Build"        cmd /k call "%ROOT_DIR%cmd\build.cmd"
    goto menu
)
if /I "%CHOICE%"=="3" (
    start "Mangadvisor - Up"           cmd /k call "%ROOT_DIR%cmd\up.cmd"
    goto menu
)
if /I "%CHOICE%"=="4" (
    start "Mangadvisor - Start"        cmd /k call "%ROOT_DIR%cmd\start.cmd"
    goto menu
)
if /I "%CHOICE%"=="5" (
    start "Mangadvisor - Status"       cmd /k call "%ROOT_DIR%cmd\status.cmd"
    goto menu
)
if /I "%CHOICE%"=="6" (
    start "Mangadvisor - Logs"         cmd /k call "%ROOT_DIR%cmd\logs.cmd"
    goto menu
)
if /I "%CHOICE%"=="7" (
    start "Mangadvisor - Stop"         cmd /k call "%ROOT_DIR%cmd\stop.cmd"
    goto menu
)
if /I "%CHOICE%"=="8" (
    start "Mangadvisor - Down"         cmd /k call "%ROOT_DIR%cmd\down.cmd"
    goto menu
)
if /I "%CHOICE%"=="9" (
    start "Mangadvisor - Restart"      cmd /k call "%ROOT_DIR%cmd\restart.cmd"
    goto menu
)
if /I "%CHOICE%"=="10" (
    start "Mangadvisor - Clean"        cmd /k call "%ROOT_DIR%cmd\clean.cmd"
    goto menu
)
if /I "%CHOICE%"=="11" (
    start "Mangadvisor - Nuke"         cmd /k call "%ROOT_DIR%cmd\nuke.cmd"
    goto menu
)
if /I "%CHOICE%"=="13" (
    start "Mangadvisor - Mobile HTTPS" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\mobile-setup.ps1"
    goto menu
)
if /I "%CHOICE%"=="14" (
    start "Mangadvisor - Stop Mobile" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\mobile-setup.ps1" -Stop
    goto menu
)
if /I "%CHOICE%"=="15" (
    start "Mangadvisor - IA locale" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\ai-setup.ps1"
    goto menu
)
if /I "%CHOICE%"=="16" (
    start "Mangadvisor - Arreter IA" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\ai-setup.ps1" -Stop
    goto menu
)
if /I "%CHOICE%"=="17" (
    start "Mangadvisor - Sauvegarde" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\library-backup.ps1" -Action Backup
    goto menu
)
if /I "%CHOICE%"=="18" (
    start "Mangadvisor - Verification sauvegarde" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\library-backup.ps1" -Action Verify
    goto menu
)
if /I "%CHOICE%"=="19" (
    start "Mangadvisor - Restauration securisee" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\library-backup.ps1" -Action Restore
    goto menu
)
if /I "%CHOICE%"=="20" (
    start "Mangadvisor - Benchmark prive" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\benchmark-mangatheque.ps1"
    goto menu
)
if /I "%CHOICE%"=="21" (
    start "Mangadvisor - Import inventaire" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\import-private-inventory.ps1"
    goto menu
)
if /I "%CHOICE%"=="22" (
    start "Mangadvisor - Installation complete" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Wizard
    goto menu
)
if /I "%CHOICE%"=="23" (
    start "Mangadvisor - Configuration" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Environment
    goto menu
)
if /I "%CHOICE%"=="24" (
    start "Mangadvisor - Initialisation SQL" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Database
    goto menu
)
if /I "%CHOICE%"=="25" (
    start "Mangadvisor - Catalogue Tenrai" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Catalogue
    goto menu
)
if /I "%CHOICE%"=="26" (
    start "Mangadvisor - Relations mangas" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Recommendations
    goto menu
)
if /I "%CHOICE%"=="27" (
    start "Mangadvisor - Diagnostic" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Diagnostic
    goto menu
)
if /I "%CHOICE%"=="28" (
    start "Mangadvisor - Mise a jour" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Update
    goto menu
)
if /I "%CHOICE%"=="29" (
    start "Mangadvisor - Diagnostic reseau" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Network
    goto menu
)
REM Ancien choix 12 : raccourci de compatibilite vers l'option 25.
if /I "%CHOICE%"=="12" (
    start "Mangadvisor - Catalogue Tenrai" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Catalogue
    goto menu
)
if /I "%CHOICE%"=="Q" goto :eof

echo.
echo Choix invalide.
pause
goto menu

:run_command
if /I "%~1"=="wizard" (
    start "Mangadvisor - Installation complete" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Wizard
    goto :eof
)
if /I "%~1"=="environment" (
    start "Mangadvisor - Configuration" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Environment
    goto :eof
)
if /I "%~1"=="database" (
    start "Mangadvisor - Initialisation SQL" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Database
    goto :eof
)
if /I "%~1"=="recommendations" (
    start "Mangadvisor - Relations mangas" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Recommendations
    goto :eof
)
if /I "%~1"=="diagnostic" (
    start "Mangadvisor - Diagnostic" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Diagnostic
    goto :eof
)
if /I "%~1"=="update" (
    start "Mangadvisor - Mise a jour" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Update
    goto :eof
)
if /I "%~1"=="network" (
    start "Mangadvisor - Diagnostic reseau" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Network
    goto :eof
)
if /I "%~1"=="check" (
    start "Mangadvisor - Verification" cmd /k call "%ROOT_DIR%cmd\install-check.cmd"
    goto :eof
)
if /I "%~1"=="build" (
    start "Mangadvisor - Build"        cmd /k call "%ROOT_DIR%cmd\build.cmd"
    goto :eof
)
if /I "%~1"=="up" (
    start "Mangadvisor - Up"           cmd /k call "%ROOT_DIR%cmd\up.cmd"
    goto :eof
)
if /I "%~1"=="start" (
    start "Mangadvisor - Start"        cmd /k call "%ROOT_DIR%cmd\start.cmd"
    goto :eof
)
if /I "%~1"=="status" (
    start "Mangadvisor - Status"       cmd /k call "%ROOT_DIR%cmd\status.cmd"
    goto :eof
)
if /I "%~1"=="logs" (
    start "Mangadvisor - Logs"         cmd /k call "%ROOT_DIR%cmd\logs.cmd"
    goto :eof
)
if /I "%~1"=="stop" (
    start "Mangadvisor - Stop"         cmd /k call "%ROOT_DIR%cmd\stop.cmd"
    goto :eof
)
if /I "%~1"=="down" (
    start "Mangadvisor - Down"         cmd /k call "%ROOT_DIR%cmd\down.cmd"
    goto :eof
)
if /I "%~1"=="restart" (
    start "Mangadvisor - Restart"      cmd /k call "%ROOT_DIR%cmd\restart.cmd"
    goto :eof
)
if /I "%~1"=="clean" (
    start "Mangadvisor - Clean"        cmd /k call "%ROOT_DIR%cmd\clean.cmd"
    goto :eof
)
if /I "%~1"=="nuke" (
    start "Mangadvisor - Nuke"         cmd /k call "%ROOT_DIR%cmd\nuke.cmd"
    goto :eof
)
if /I "%~1"=="mobile" (
    start "Mangadvisor - Mobile HTTPS" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\mobile-setup.ps1"
    goto :eof
)
if /I "%~1"=="ai" (
    start "Mangadvisor - IA locale" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\ai-setup.ps1"
    goto :eof
)
if /I "%~1"=="ai-stop" (
    start "Mangadvisor - Arreter IA" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\ai-setup.ps1" -Stop
    goto :eof
)
if /I "%~1"=="mobile-stop" (
    start "Mangadvisor - Stop Mobile" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\mobile-setup.ps1" -Stop
    goto :eof
)
REM Entree catalogue unique + aliases historiques non destructifs.
if /I "%~1"=="catalogue" (
    start "Mangadvisor - Catalogue Tenrai" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Catalogue
    goto :eof
)
if /I "%~1"=="jikan" (
    start "Mangadvisor - Catalogue Tenrai" cmd /k powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action Catalogue
    goto :eof
)
if /I "%~1"=="jikan-reset" (
    echo Ancienne option destructive desactivee. Utilise l'option 25.
    exit /b 1
)
if /I "%~1"=="jikan-pages" (
    echo Ancienne commande remplacee. Utilise l'option 25 pour les pages.
    exit /b 1
)

echo Commande inconnue : %~1
echo.
echo Commandes disponibles :
echo   check ^| build ^| up ^| start ^| status ^| logs ^| stop ^| down ^| restart ^| clean ^| nuke
echo   catalogue ^| jikan (alias historique) ^| network ^| diagnostic
echo   mobile ^| mobile-stop
exit /b 1

endlocal