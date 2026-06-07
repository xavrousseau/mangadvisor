@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo      Mangadvisor - Nettoyage standard
echo ==================================================
echo.
echo Cette action supprime :
echo - les conteneurs
echo - les images locales construites
echo.
echo Elle conserve :
echo - les volumes de donnees
echo.

set /p CONFIRM=Continuer ? Tape OUI pour confirmer : 

if /I not "%CONFIRM%"=="OUI" (
    echo Operation annulee.
    exit /b 0
)

pushd "%ROOT_DIR%"
%COMPOSE_CMD% down --rmi local
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%