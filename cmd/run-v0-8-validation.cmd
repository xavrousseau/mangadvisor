@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo   Mangadvisor - Validation globale V0.8
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

docker ps --filter "name=mangadvisor_api" --format "{{.Names}}" | findstr /I "mangadvisor_api" >nul

if errorlevel 1 (
    echo.
    echo ERREUR : le conteneur mangadvisor_api ne semble pas demarre.
    echo Lance d'abord :
    echo   mangadvisor.cmd up
    echo.
    pause
    exit /b 1
)

echo --------------------------------------------------
echo 1/6 - Tests profils de recommandation
echo --------------------------------------------------
python pipelines\engine\scripts\run_recommendation_profile_tests.py

if errorlevel 1 (
    echo ERREUR : echec tests profils de recommandation.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 2/6 - Tests recommandations depuis bibliotheque
echo --------------------------------------------------
python pipelines\engine\scripts\run_library_recommendation_tests.py --reset-library

if errorlevel 1 (
    echo ERREUR : echec tests recommandations bibliotheque.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 3/6 - Tests objectifs de recommandation
echo --------------------------------------------------
python pipelines\engine\scripts\run_library_goal_tests.py --reset-library

if errorlevel 1 (
    echo ERREUR : echec tests objectifs bibliotheque.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 4/6 - Tests statuts bibliotheque
echo --------------------------------------------------
python pipelines\engine\scripts\run_library_status_tests.py --reset-library

if errorlevel 1 (
    echo ERREUR : echec tests statuts bibliotheque.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 5/6 - Tests import bibliotheque
echo --------------------------------------------------
python pipelines\engine\scripts\run_library_import_tests.py --reset-library

if errorlevel 1 (
    echo ERREUR : echec tests import bibliotheque.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 6/6 - Tests robustesse import bibliotheque
echo --------------------------------------------------
python pipelines\engine\scripts\run_library_import_robustness_tests.py --reset-library

if errorlevel 1 (
    echo ERREUR : echec tests robustesse import bibliotheque.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo   Validation globale V0.8 terminee avec succes
echo ==================================================
echo.
echo Rapports disponibles dans :
echo   docs\reports
echo.
pause

endlocal