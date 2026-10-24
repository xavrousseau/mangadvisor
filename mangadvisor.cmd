@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT_DIR=%~dp0"

rem A single synchronous entry point: never spawn detached terminal windows.
rem Everything destructive is deliberately absent from the everyday menu.
if not "%~1"=="" goto :direct

:menu
cls
set "CODE_REV=non disponible"
for /f "delims=" %%H in ('git -C "%ROOT_DIR%" rev-parse --short HEAD 2^>nul') do set "CODE_REV=%%H"
echo ==========================================================
echo                       MANGADVISOR
echo ==========================================================
echo   Version Git locale : %CODE_REV%
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
echo                ESPACE DE GESTION
echo ==========================================================
echo.
echo    1 - Catalogue general et recherche
echo    2 - Ma bibliotheque et mes imports
echo    3 - Fonctions facultatives
echo    S - Entretien, diagnostic et restauration
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto menu
if /I "%CHOICE%"=="1" goto :catalogue_menu
if /I "%CHOICE%"=="2" goto :library_menu
if /I "%CHOICE%"=="3" goto :optional_menu
if /I "%CHOICE%"=="S" goto :maintenance
echo Choix inconnu.
pause
goto advanced
:catalogue_menu
cls
echo ==========================================================
echo             CATALOGUE ET RECHERCHE
echo ==========================================================
echo.
echo    1 - Actualiser les mangas et les nouveautes
echo    2 - Actualiser le moteur de recherche
echo    3 - Exporter la base bibliographique publique
echo    4 - Lire le bilan du referentiel public
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto advanced
set "KEY="
if "%CHOICE%"=="1" set "KEY=catalogue-lifecycle"
if "%CHOICE%"=="2" set "KEY=search-index"
if "%CHOICE%"=="3" set "KEY=catalogue-export"
if "%CHOICE%"=="4" set "KEY=catalogue-graph-report"
if not defined KEY (
    echo Choix inconnu.
    pause
    goto catalogue_menu
)
call :dispatch "%KEY%"
call :result
goto catalogue_menu

:library_menu
cls
echo ==========================================================
echo                 MA BIBLIOTHEQUE
echo ==========================================================
echo.
echo    1 - Importer mon inventaire CSV
echo    2 - Simuler mon import sans rien modifier
echo    3 - Sauvegarder mes donnees
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto advanced
set "KEY="
if "%CHOICE%"=="1" set "KEY=import"
if "%CHOICE%"=="2" set "KEY=benchmark"
if "%CHOICE%"=="3" set "KEY=backup"
if not defined KEY (
    echo Choix inconnu.
    pause
    goto library_menu
)
call :dispatch "%KEY%"
call :result
goto library_menu

:optional_menu
cls
echo ==========================================================
echo               FONCTIONS FACULTATIVES
echo ==========================================================
echo.
echo    1 - Activer le scanner mobile
echo    2 - Arreter le scanner mobile
echo    3 - Activer le conseiller IA local
echo    4 - Arreter le conseiller IA local
echo    5 - Actualiser les recommandations
echo    0 - Retour
echo.
set "CHOICE="
set /p "CHOICE=Ton choix : "
if /I "%CHOICE%"=="0" goto advanced
set "KEY="
if "%CHOICE%"=="1" set "KEY=mobile"
if "%CHOICE%"=="2" set "KEY=mobile-stop"
if "%CHOICE%"=="3" set "KEY=ai"
if "%CHOICE%"=="4" set "KEY=ai-stop"
if "%CHOICE%"=="5" set "KEY=recommendations"
if not defined KEY (
    echo Choix inconnu.
    pause
    goto optional_menu
)
call :dispatch "%KEY%"
call :result
goto optional_menu

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
if /I "%~1"=="sources-benchmark" set "ACTION=SourcesBenchmarkV2"
if /I "%~1"=="sources-benchmark-v2" set "ACTION=SourcesBenchmarkV2"
if /I "%~1"=="bibliographic-staging" set "ACTION=BibliographicStaging"
if /I "%~1"=="complete-mal-catalogue" set "ACTION=CompleteMALCatalogue"
if /I "%~1"=="catalogue-french-scrinis" set "ACTION=CatalogueFrenchScrinis"
if /I "%~1"=="bibliography-pilot" set "ACTION=BibliographyPilot"
if /I "%~1"=="catalogue-export" set "PS_SCRIPT=export-catalogue-public.ps1"
if /I "%~1"=="catalogue-source-graph" set "PS_SCRIPT=rebuild-catalogue-source-graph.ps1"
if /I "%~1"=="catalogue-graph-report" set "PS_SCRIPT=report-catalogue-source-graph.ps1"
if /I "%~1"=="catalogue-lifecycle" set "ACTION=CatalogueLifecycle"
if /I "%~1"=="search-index" set "ACTION=SearchIndex"
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
if /I "%~1"=="logs" set "ACTION=Logs"
if /I "%~1"=="status" set "ACTION=Status"
if /I "%~1"=="environment" set "ACTION=Environment"
if /I "%~1"=="database" set "ACTION=Database"
if /I "%~1"=="verify-backup" set "PS_SCRIPT=library-backup.ps1"
if /I "%~1"=="verify-backup" set "PS_ARGS=-Action Verify"
if /I "%~1"=="restore" set "PS_SCRIPT=library-backup.ps1"
if /I "%~1"=="restore" set "PS_ARGS=-Action Restore"
if /I "%~1"=="network" set "ACTION=Network"

rem A few safe aliases for existing launch instructions.
if /I "%~1"=="up" set "ACTION=Start"
rem Legacy Docker aliases are deliberately retired: use update/start/stop/status.

if /I "%~1"=="help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--help" goto :help
if /I "%~1"=="nuke" goto :blocked
if /I "%~1"=="clean" goto :blocked
if /I "%~1"=="jikan-reset" goto :blocked
if defined ACTION goto :execute_control
if defined PS_SCRIPT goto :execute_powershell
echo Commande inconnue : %~1
echo Utilise mangadvisor.cmd help pour afficher les commandes.
exit /b 1

:execute_control
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\control-center.ps1" -Action "%ACTION%"
exit /b %ERRORLEVEL%

:execute_powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%cmd\%PS_SCRIPT%" %PS_ARGS%
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
echo          bnf-enrich, bnf-bulk, sources-benchmark, sources-benchmark-v2,
echo          bibliographic-staging, complete-mal-catalogue,
echo          catalogue-french-scrinis, bibliography-pilot,
echo          catalogue-lifecycle, search-index, catalogue-export, catalogue-source-graph,
echo          catalogue-graph-report,
echo          wikidata-enrich, library-enrich, multilingual-aliases,
echo          mobile, mobile-stop, ai, ai-stop, status, logs,
echo          environment, database, network, verify-backup, restore.
echo La suppression des volumes n'est jamais proposee.
exit /b 0
