@echo off
setlocal
call "%~dp0common.cmd"
call "%~dp0install-check.cmd"
if errorlevel 1 exit /b 1

echo ==================================================
echo      Mangadvisor - Build + demarrage stack
echo ==================================================
echo.

pushd "%ROOT_DIR%"
rem Retire seulement le conteneur Streamlit historique, jamais les volumes.
call "%~dp0retire-legacy-ui.cmd"
if errorlevel 1 (
  popd
  exit /b 1
)
%COMPOSE_CMD% up --build
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%