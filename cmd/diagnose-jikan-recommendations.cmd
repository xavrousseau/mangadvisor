@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo   Mangadvisor - Diagnose Jikan Recommendations
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

docker ps --filter "name=mangadvisor_postgres" --format "{{.Names}}" | findstr /I "mangadvisor_postgres" >nul

if errorlevel 1 (
    echo.
    echo ERREUR : le conteneur mangadvisor_postgres ne semble pas demarre.
    echo Lance d'abord la stack avec mangadvisor.cmd ou docker compose.
    echo.
    pause
    exit /b 1
)

python pipelines\engine\scripts\analyze_jikan_recommendation_edges.py

if errorlevel 1 (
    echo.
    echo ERREUR : echec diagnostic recommandations Jikan.
    pause
    exit /b 1
)

echo.
echo Diagnostic termine.
echo Rapport genere dans docs\reports\jikan_recommendation_edges_diagnostic.md
echo.
pause

endlocal