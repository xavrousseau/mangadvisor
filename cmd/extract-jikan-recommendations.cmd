@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

REM ==================================================
REM Parametres extraction recommandations Jikan
REM ==================================================
set "LIMIT_ITEMS=50"
set "OFFSET=0"
set "SLEEP_SECONDS=1"

echo ==================================================
echo   Mangadvisor - Extract Jikan Recommendations
echo ==================================================
echo.
echo Projet      : %ROOT_DIR%
echo Limit items : %LIMIT_ITEMS%
echo Offset      : %OFFSET%
echo Sleep       : %SLEEP_SECONDS%s
echo.

echo --------------------------------------------------
echo Verification PostgreSQL
echo --------------------------------------------------

docker ps --filter "name=mangadvisor_postgres" --format "{{.Names}}" | findstr /I "mangadvisor_postgres" >nul

if errorlevel 1 (
    echo.
    echo ERREUR : le conteneur mangadvisor_postgres ne semble pas demarre.
    echo Lance d'abord la stack avec mangadvisor.cmd ou docker compose.
    echo.
    pause
    exit /b 1
)

echo OK : PostgreSQL est demarre.
echo.

echo --------------------------------------------------
echo Extraction recommandations Jikan
echo --------------------------------------------------

python pipelines\engine\scripts\extract_jikan_recommendations.py ^
    --limit-items %LIMIT_ITEMS% ^
    --offset %OFFSET% ^
    --sleep-seconds %SLEEP_SECONDS%

if errorlevel 1 (
    echo.
    echo ERREUR : echec extraction recommandations Jikan.
    pause
    exit /b 1
)

echo.
echo Extraction recommandations terminee.
echo Fichiers disponibles dans data\raw\jikan\recommendations.
echo.
pause

endlocal