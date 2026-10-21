@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT_DIR=%~dp0"

rem A single synchronous entry point: never spawn detached terminal windows.
rem Everything destructive is deliberately absent from the everyday menu.
if not "%~1"=="" goto :direct

:menu
cls
echo ==========================================================
echo                       MANGADVISOR
echo ==========================================================
echo.
echo    1 - Premiere installation (guidage complet)
echo    2 - Demarrer et ouvrir Mangadvisor
echo    3 - Mettre a jour sans perdre mes donnees
echo    4 - Sauvegarder ma mangatheque
echo    5 - Verifier que tout fonctionne
echo    6 - Arreter Mangadvisor
echo    7 - Recuperer la derniere version depuis GitHub (code uniquement)
echo.
echo    A - Options avancees
echo    0 - Quitter
echo.
echo ==========================================================
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" exit /b 0
if /I "%CHOICE%"=="Q" exit /b 0
if /I "%CHOICE%"=="A" goto :advanced

set "KEY="
if "%CHOICE%"=="1" set "KEY=install"
if "%CHOICE%"=="2" set "KEY=start"
if "%CHOICE%"=="3" set "KEY=update"
if "%CHOICE%"=="4" set "KEY=backup"
if "%CHOICE%"=="5" set "KEY=diagnostic"
if "%CHOICE%"=="6" set "KEY=stop"
if "%CHOICE%"=="7" set "KEY=github-sync"
if not defined KEY (
    echo Choix inconnu. Utilise 0, 1 a 7 ou A.
    pause
    goto menu
)
call :dispatch "%KEY%"
call :result
goto menu

:advanced
cls
echo ==========================================================
echo                  OUTILS AVANCES
echo ==========================================================
echo.
echo    1 - Actualiser le catalogue de mangas
echo    2 - Actualiser les recommandations communautaires
echo    3 - Importer ma mangatheque depuis le CSV
echo    4 - Tester ma mangatheque sans la modifier
echo    5 - Activer le scanner mobile HTTPS
echo    6 - Arreter le scanner mobile HTTPS
echo    7 - Activer le conseiller IA local
echo    8 - Arreter le conseiller IA local
echo    9 - Consulter les journaux Docker
echo   10 - Enrichir les fiches via la BnF (candidats a verifier)
echo   11 - Completer les informations depuis Wikidata (titres FR, genres)
echo   12 - Enrichir ma mangatheque automatiquement (Wikidata et BnF)
echo   13 - Recuperer les titres alternatifs FR, EN et JA
echo   14 - Etendre le catalogue Tenrai (mangas et one-shots)
echo   15 - Importer des fichiers bibliographiques BnF (candidats)
echo   19 - Charger tout le catalogue MAL/Jikan via Tenrai (avec reprise)
echo   20 - Enrichir les titres FR du catalogue via Scrinis (direct)
echo   21 - Catalogue vivant : nouveautes et veille automatique
echo.
echo    S - Entretien, configuration et restauration
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto menu
if /I "%CHOICE%"=="S" goto :maintenance

set "KEY="
if "%CHOICE%"=="1" set "KEY=catalogue"
if "%CHOICE%"=="2" set "KEY=recommendations"
if "%CHOICE%"=="3" set "KEY=import"
if "%CHOICE%"=="4" set "KEY=benchmark"
if "%CHOICE%"=="5" set "KEY=mobile"
if "%CHOICE%"=="6" set "KEY=mobile-stop"
if "%CHOICE%"=="7" set "KEY=ai"
if "%CHOICE%"=="8" set "KEY=ai-stop"
if "%CHOICE%"=="9" set "KEY=logs"
if "%CHOICE%"=="10" set "KEY=bnf-enrich"
if "%CHOICE%"=="11" set "KEY=wikidata-enrich"
if "%CHOICE%"=="12" set "KEY=library-enrich"
if "%CHOICE%"=="13" set "KEY=multilingual-aliases"
if "%CHOICE%"=="14" set "KEY=catalogue-extended"
if "%CHOICE%"=="15" set "KEY=bnf-bulk"
if "%CHOICE%"=="19" set "KEY=complete-mal-catalogue"
if "%CHOICE%"=="20" set "KEY=catalogue-french-scrinis"
if "%CHOICE%"=="21" set "KEY=catalogue-lifecycle"
if not defined KEY (
    echo Choix inconnu.
    pause
    goto advanced
)
call :dispatch "%KEY%"
call :result
goto advanced

:maintenance
cls
echo ==========================================================
echo                 ENTRETIEN ET SECOURS
echo ==========================================================
echo.
echo    1 - Etat des services Docker
echo    2 - Configurer ou verifier les variables .env
echo    3 - Initialiser ou reparer les tables SQL
echo    4 - Verifier la derniere sauvegarde
echo    5 - Restaurer une sauvegarde (confirmation requise)
echo    6 - Tester l'acces reseau au fournisseur manga
echo.
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto advanced
set "KEY="
if "%CHOICE%"=="1" set "KEY=status"
if "%CHOICE%"=="2" set "KEY=environment"
if "%CHOICE%"=="3" set "KEY=database"
if "%CHOICE%"=="4" set "KEY=verify-backup"
if "%CHOICE%"=="5" set "KEY=restore"
if "%CHOICE%"=="6" set "KEY=network"
if not defined KEY (
    echo Choix inconnu.
    pause
    goto maintenance
)
call :dispatch "%KEY%"
call :result
goto maintenance

:result
rem Ne jamais placer du texte avec parentheses dans un bloc IF (...) ELSE (...).
rem Sous cmd.exe, une parenthese non echappee dans ECHO peut interrompre
rem le script avant PAUSE et fermer la fenetre (constate apres A / 11).
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" echo Operation terminee.
if not "%RC%"=="0" echo ECHEC - code %RC%. Lis le message ci-dessus.
if not "%RC%"=="0" echo Aucune suppression automatique des donnees n'a ete lancee.
echo.
pause
exit /b 0

:direct
call :dispatch "%~1"
exit /b %ERRORLEVEL%

:dispatch
rem Command aliases remain available to scripts and to experienced users.
set "ACTION="
set "PS_SCRIPT="
set "PS_ARGS="
set "CMD_SCRIPT="
if /I "%~1"=="install" set "ACTION=Wizard"
if /I "%~1"=="wizard" set "ACTION=Wizard"
if /I "%~1"=="start" set "ACTION=Start"
if /I "%~1"=="update" set "ACTION=Update"
if /I "%~1"=="github-sync" set "PS_SCRIPT=github-sync.ps1"
if /I "%~1"=="backup" set "PS_SCRIPT=library-backup.ps1"
if /I "%~1"=="backup" set "PS_ARGS=-Action Backup"
if /I "%~1"=="diagnostic" set "ACTION=Diagnostic"
if /I "%~1"=="stop" set "ACTION=Stop"
if /I "%~1"=="catalogue" set "ACTION=Catalogue"
if /I "%~1"=="catalogue-extended" set "ACTION=CatalogueExtended"
if /I "%~1"=="jikan" set "ACTION=Catalogue"
if /I "%~1"=="recommendations" set "ACTION=Recommendations"
if /I "%~1"=="import" set "ACTION=Inventory"
if /I "%~1"=="bnf-enrich" set "ACTION=BnF"
if /I "%~1"=="bnf-bulk" set "ACTION=BnFBulk"
if /I "%~1"=="complete-mal-catalogue" set "ACTION=CompleteMALCatalogue"
if /I "%~1"=="catalogue-french-scrinis" set "ACTION=CatalogueFrenchScrinis"
if /I "%~1"=="catalogue-lifecycle" set "ACTION=CatalogueLifecycle"
if /I "%~1"=="wikidata-enrich" set "ACTION=Wikidata"
if /I "%~1"=="library-enrich" set "ACTION=LibraryEnrichment"
if /I "%~1"=="multilingual-aliases" set "ACTION=Aliases"
if /I "%~1"=="benchmark" set "PS_SCRIPT=benchmark-mangatheque.ps1"
if /I "%~1"=="mobile" set "PS_SCRIPT=mobile-setup.ps1"
if /I "%~1"=="mobile-stop" set "PS_SCRIPT=mobile-setup.ps1"
if /I "%~1"=="mobile-stop" set "PS_ARGS=-Stop"
if /I "%~1"=="ai" set "PS_SCRIPT=ai-setup.ps1"
if /I "%~1"=="ai-stop" set "PS_SCRIPT=ai-setup.ps1"
if /I "%~1"=="ai-stop" set "PS_ARGS=-Stop"
if /I "%~1"=="logs" set "CMD_SCRIPT=logs.cmd"
if /I "%~1"=="status" set "CMD_SCRIPT=status.cmd"
if /I "%~1"=="environment" set "ACTION=Environment"
if /I "%~1"=="database" set "ACTION=Database"
if /I "%~1"=="verify-backup" set "PS_SCRIPT=library-backup.ps1"
if /I "%~1"=="verify-backup" set "PS_ARGS=-Action Verify"
if /I "%~1"=="restore" set "PS_SCRIPT=library-backup.ps1"
if /I "%~1"=="restore" set "PS_ARGS=-Action Restore"
if /I "%~1"=="network" set "ACTION=Network"

rem A few safe aliases for existing launch instructions.
if /I "%~1"=="up" set "ACTION=Start"
if /I "%~1"=="check" set "CMD_SCRIPT=install-check.cmd"
if /I "%~1"=="build" set "CMD_SCRIPT=build.cmd"
if /I "%~1"=="down" set "CMD_SCRIPT=down.cmd"
if /I "%~1"=="restart" set "CMD_SCRIPT=restart.cmd"

if /I "%~1"=="help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--help" goto :help
if /I "%~1"=="nuke" goto :blocked
if /I "%~1"=="clean" goto :blocked
if /I "%~1"=="jikan-reset" goto :blocked
if defined ACTION goto :execute_control
if defined PS_SCRIPT goto :execute_powershell
if defined CMD_SCRIPT goto :execute_command
echo Commande inconnue : %~1
echo Utilise mangadvisor.cmd help pour afficher les commandes.
exit /b 1

:execute_control
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action "%ACTION%"
exit /b %ERRORLEVEL%

:execute_powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\%PS_SCRIPT%" %PS_ARGS%
exit /b %ERRORLEVEL%

:execute_command
call "%ROOT_DIR%cmd\%CMD_SCRIPT%"
exit /b %ERRORLEVEL%

:blocked
echo Commande dangereuse ou obsolete non disponible dans ce lanceur.
echo Aucune donnees Docker ou personnelle n'a ete supprimee.
exit /b 1

:help
echo Mangadvisor : ouvre mangadvisor.cmd sans argument pour le menu.
echo.
echo   install          Premiere installation guidee
echo   start            Demarrer et ouvrir le site
echo   update           Sauvegarder, recuperer GitHub, reconstruire et verifier
echo   github-sync      Recuperer uniquement le code GitHub, archives en securite
echo   backup           Sauvegarder et tester la restauration
echo   diagnostic       Verifier l'application
echo   stop             Arreter sans supprimer les volumes
echo.
echo Autres : catalogue, catalogue-extended, recommendations, import, benchmark,
echo          bnf-enrich, bnf-bulk, 
echo          complete-mal-catalogue,
echo          catalogue-french-scrinis, catalogue-lifecycle,
echo          wikidata-enrich, library-enrich, multilingual-aliases,
echo          mobile, mobile-stop, ai, ai-stop, status, logs,
echo          environment, database, network, verify-backup, restore.
echo La suppression des volumes n'est jamais proposee.
exit /b 0
