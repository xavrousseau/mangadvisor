@echo off
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI"

set "COMPOSE_FILE_1=%ROOT_DIR%\infra\compose\docker-compose.yml"
set "COMPOSE_FILE_2=%ROOT_DIR%\infra\compose\docker-compose.dev.yml"
set "ENV_FILE=%ROOT_DIR%\.env"

rem L'IA n'est incluse au demarrage normal qu'apres l'activation explicite.
rem Les options 3/4/7/8/9 tiennent ainsi compte du choix de l'utilisateur.
set "AI_PROFILE="
if exist "%ENV_FILE%" (
    findstr /I /X /C:"OLLAMA_ENABLED=true" "%ENV_FILE%" >nul
    if not errorlevel 1 set "AI_PROFILE=--profile ai"
)
set "COMPOSE_CMD=docker compose %AI_PROFILE% --env-file "%ENV_FILE%" -f "%COMPOSE_FILE_1%" -f "%COMPOSE_FILE_2%""
exit /b 0