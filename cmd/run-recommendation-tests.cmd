@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo      Mangadvisor - Recommendation Tests
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

python pipelines\engine\scripts\run_recommendation_profile_tests.py

if errorlevel 1 (
    echo.
    echo ERREUR : les tests de recommandation ont echoue.
    pause
    exit /b 1
)

echo.
echo Tests termines avec succes.
echo Rapport genere dans docs\reports.
echo.
pause

endlocal