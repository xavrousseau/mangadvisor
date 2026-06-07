@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo   Mangadvisor - Tests objectifs recommandations
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

python pipelines\engine\scripts\run_library_goal_tests.py --reset-library

if errorlevel 1 (
    echo.
    echo ERREUR : echec des tests objectifs recommandations.
    pause
    exit /b 1
)

echo.
echo Rapport genere dans docs\reports\library_goal_tests_v0_8_3.md
echo.
pause

endlocal