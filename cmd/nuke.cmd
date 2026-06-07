@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo       Mangadvisor - Nettoyage complet
echo ==================================================
echo.
echo ATTENTION :
echo Cette action supprime :
echo - les conteneurs
echo - les images locales construites
echo - les volumes Docker
echo.
echo Les donnees PostgreSQL et Meilisearch seront perdues.
echo.

set /p CONFIRM=Tape OUI pour continuer : 

if /I not "%CONFIRM%"=="OUI" (
    echo Operation annulee.
    exit /b 0
)

pushd "%ROOT_DIR%"
%COMPOSE_CMD% down --volumes --rmi local
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%