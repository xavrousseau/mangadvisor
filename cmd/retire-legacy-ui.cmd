@echo off
setlocal
rem Migration non destructive depuis l'ancien conteneur Streamlit port 8502.
rem Le service ui existe uniquement dans l'overlay de developpement.
rem Aucune option --volumes / -v et aucun acces aux donnees PostgreSQL.
call "%~dp0common.cmd"
set "DEV_COMPOSE=%ROOT_DIR%\infra\compose\docker-compose.dev.yml"
pushd "%ROOT_DIR%"
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE_1%" -f "%DEV_COMPOSE%" --profile legacy stop ui
if errorlevel 1 (
  popd
  endlocal & exit /b 1
)
docker compose --env-file "%ENV_FILE%" -f "%COMPOSE_FILE_1%" -f "%DEV_COMPOSE%" --profile legacy rm -f ui
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
