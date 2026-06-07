@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo        Mangadvisor - Verification environnement
echo ==================================================
echo.

docker --version
if errorlevel 1 (
    echo.
    echo ERREUR : Docker n'est pas disponible.
    exit /b 1
)

echo.
docker compose version
if errorlevel 1 (
    echo.
    echo ERREUR : Docker Compose n'est pas disponible.
    exit /b 1
)

echo.
if not exist "%ENV_FILE%" (
    echo ERREUR : fichier .env introuvable :
    echo %ENV_FILE%
    exit /b 1
)

if not exist "%COMPOSE_FILE_1%" (
    echo ERREUR : fichier introuvable :
    echo %COMPOSE_FILE_1%
    exit /b 1
)

if not exist "%COMPOSE_FILE_2%" (
    echo ERREUR : fichier introuvable :
    echo %COMPOSE_FILE_2%
    exit /b 1
)

echo OK : environnement pret.
endlocal
exit /b 0