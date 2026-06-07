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
echo   Pipeline
echo   --------
echo   12 - Run Jikan Pipeline
echo.
echo   Q  - Quitter
echo.
echo ============================================================
echo Exemples de commandes directes :
echo   mangadvisor.cmd check
echo   mangadvisor.cmd build
echo   mangadvisor.cmd start
echo   mangadvisor.cmd logs
echo   mangadvisor.cmd jikan
echo   mangadvisor.cmd jikan-reset
echo ============================================================
echo.

set /p CHOICE=Votre choix : 

if /I "%CHOICE%"=="1"  start "Mangadvisor - Verification" cmd /k call "%ROOT_DIR%cmd\install-check.cmd" & goto menu
if /I "%CHOICE%"=="2"  start "Mangadvisor - Build"        cmd /k call "%ROOT_DIR%cmd\build.cmd" & goto menu
if /I "%CHOICE%"=="3"  start "Mangadvisor - Up"           cmd /k call "%ROOT_DIR%cmd\up.cmd" & goto menu
if /I "%CHOICE%"=="4"  start "Mangadvisor - Start"        cmd /k call "%ROOT_DIR%cmd\start.cmd" & goto menu
if /I "%CHOICE%"=="5"  start "Mangadvisor - Status"       cmd /k call "%ROOT_DIR%cmd\status.cmd" & goto menu
if /I "%CHOICE%"=="6"  start "Mangadvisor - Logs"         cmd /k call "%ROOT_DIR%cmd\logs.cmd" & goto menu
if /I "%CHOICE%"=="7"  start "Mangadvisor - Stop"         cmd /k call "%ROOT_DIR%cmd\stop.cmd" & goto menu
if /I "%CHOICE%"=="8"  start "Mangadvisor - Down"         cmd /k call "%ROOT_DIR%cmd\down.cmd" & goto menu
if /I "%CHOICE%"=="9"  start "Mangadvisor - Restart"      cmd /k call "%ROOT_DIR%cmd\restart.cmd" & goto menu
if /I "%CHOICE%"=="10" start "Mangadvisor - Clean"        cmd /k call "%ROOT_DIR%cmd\clean.cmd" & goto menu
if /I "%CHOICE%"=="11" start "Mangadvisor - Nuke"         cmd /k call "%ROOT_DIR%cmd\nuke.cmd" & goto menu

if /I "%CHOICE%"=="12" goto jikan_menu

if /I "%CHOICE%"=="Q" goto :eof

echo.
echo Choix invalide.
pause
goto menu

:jikan_menu
cls
echo ============================================================
echo                    MANGADVISOR - JIKAN PIPELINE
echo ============================================================
echo.
echo   1 - Run Jikan Pipeline (1 page, limit 25)
echo   2 - Run Jikan Pipeline (pages 1 a 3, limit 10)
echo   3 - Run Jikan Pipeline + reset DB (pages 1 a 3, limit 10)
echo   4 - Run Jikan Pipeline personnalise
echo.
echo   B - Retour menu principal
echo.
echo ============================================================
echo Exemples directs :
echo   mangadvisor.cmd jikan
echo   mangadvisor.cmd jikan-reset
echo   mangadvisor.cmd jikan-pages 1 3 10
echo ============================================================
echo.

set /p JIKAN_CHOICE=Votre choix : 

if /I "%JIKAN_CHOICE%"=="1" start "Mangadvisor - Jikan Pipeline" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" & goto menu
if /I "%JIKAN_CHOICE%"=="2" start "Mangadvisor - Jikan Pipeline 1-3" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --start-page 1 --end-page 3 --limit 10 & goto menu
if /I "%JIKAN_CHOICE%"=="3" start "Mangadvisor - Jikan Pipeline Reset" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --reset-db --start-page 1 --end-page 3 --limit 10 & goto menu
if /I "%JIKAN_CHOICE%"=="4" goto jikan_custom
if /I "%JIKAN_CHOICE%"=="B" goto menu

echo.
echo Choix invalide.
pause
goto jikan_menu

:jikan_custom
cls
echo ============================================================
echo              MANGADVISOR - JIKAN PIPELINE PERSONNALISE
echo ============================================================
echo.

set "START_PAGE=1"
set "END_PAGE=1"
set "LIMIT=25"
set "RESET_DB=non"

set /p START_PAGE=Premiere page [1] : 
if "%START_PAGE%"=="" set "START_PAGE=1"

set /p END_PAGE=Derniere page [1] : 
if "%END_PAGE%"=="" set "END_PAGE=1"

set /p LIMIT=Limite par page [25] : 
if "%LIMIT%"=="" set "LIMIT=25"

set /p RESET_DB=Reset DB avant chargement ? (oui/non) [non] : 
if "%RESET_DB%"=="" set "RESET_DB=non"

echo.
echo Recapitulatif :
echo   Start page : %START_PAGE%
echo   End page   : %END_PAGE%
echo   Limit      : %LIMIT%
echo   Reset DB   : %RESET_DB%
echo.

if /I "%RESET_DB%"=="oui" (
    start "Mangadvisor - Jikan Pipeline Custom Reset" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --reset-db --start-page %START_PAGE% --end-page %END_PAGE% --limit %LIMIT%
) else (
    start "Mangadvisor - Jikan Pipeline Custom" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --start-page %START_PAGE% --end-page %END_PAGE% --limit %LIMIT%
)

goto menu

:run_command
if /I "%~1"=="check"   start "Mangadvisor - Verification" cmd /k call "%ROOT_DIR%cmd\install-check.cmd" & goto :eof
if /I "%~1"=="build"   start "Mangadvisor - Build"        cmd /k call "%ROOT_DIR%cmd\build.cmd" & goto :eof
if /I "%~1"=="up"      start "Mangadvisor - Up"           cmd /k call "%ROOT_DIR%cmd\up.cmd" & goto :eof
if /I "%~1"=="start"   start "Mangadvisor - Start"        cmd /k call "%ROOT_DIR%cmd\start.cmd" & goto :eof
if /I "%~1"=="status"  start "Mangadvisor - Status"       cmd /k call "%ROOT_DIR%cmd\status.cmd" & goto :eof
if /I "%~1"=="logs"    start "Mangadvisor - Logs"         cmd /k call "%ROOT_DIR%cmd\logs.cmd" & goto :eof
if /I "%~1"=="stop"    start "Mangadvisor - Stop"         cmd /k call "%ROOT_DIR%cmd\stop.cmd" & goto :eof
if /I "%~1"=="down"    start "Mangadvisor - Down"         cmd /k call "%ROOT_DIR%cmd\down.cmd" & goto :eof
if /I "%~1"=="restart" start "Mangadvisor - Restart"      cmd /k call "%ROOT_DIR%cmd\restart.cmd" & goto :eof
if /I "%~1"=="clean"   start "Mangadvisor - Clean"        cmd /k call "%ROOT_DIR%cmd\clean.cmd" & goto :eof
if /I "%~1"=="nuke"    start "Mangadvisor - Nuke"         cmd /k call "%ROOT_DIR%cmd\nuke.cmd" & goto :eof

if /I "%~1"=="jikan"       start "Mangadvisor - Jikan Pipeline" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" & goto :eof
if /I "%~1"=="jikan-reset" start "Mangadvisor - Jikan Reset"    cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --reset-db --start-page 1 --end-page 3 --limit 10 & goto :eof

if /I "%~1"=="jikan-pages" (
    if "%~2"=="" (
        echo ERREUR : start-page manquant.
        exit /b 1
    )
    if "%~3"=="" (
        echo ERREUR : end-page manquant.
        exit /b 1
    )
    if "%~4"=="" (
        echo ERREUR : limit manquante.
        exit /b 1
    )
    start "Mangadvisor - Jikan Pages" cmd /k call "%ROOT_DIR%cmd\run-jikan-pipeline.cmd" --start-page %~2 --end-page %~3 --limit %~4
    goto :eof
)

echo Commande inconnue : %~1
echo.
echo Commandes disponibles :
echo   check ^| build ^| up ^| start ^| status ^| logs ^| stop ^| down ^| restart ^| clean ^| nuke
echo   jikan ^| jikan-reset ^| jikan-pages START END LIMIT
exit /b 1

endlocal