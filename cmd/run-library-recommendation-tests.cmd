@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo   Mangadvisor - Tests recommandations bibliotheque
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

docker ps --filter "name=mangadvisor_api" --format "{{.Names}}" | findstr /I "mangadvisor_api" >nul

if errorlevel 1 (
    echo.
    echo ERREUR : le conteneur mangadvisor_api ne semble pas demarre.
    echo Lance d'abord la stack avec mangadvisor.cmd.
    echo.
    pause
    exit /b 1
)

python pipelines\engine\scripts\run_library_recommendation_tests.py --reset-library

if errorlevel 1 (
    echo.
    echo ERREUR : echec des tests recommandations bibliotheque.
    pause
    exit /b 1
)

echo.
echo Rapport genere dans docs\reports\library_recommendation_tests_v0_8_2_profile_summary.md
echo.
pause

endlocal