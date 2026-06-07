@echo off
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI"

set "COMPOSE_FILE_1=%ROOT_DIR%\infra\compose\docker-compose.yml"
set "COMPOSE_FILE_2=%ROOT_DIR%\infra\compose\docker-compose.dev.yml"
set "ENV_FILE=%ROOT_DIR%\.env"

set "COMPOSE_CMD=docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE_1%" -f "%COMPOSE_FILE_2%""
exit /b 0