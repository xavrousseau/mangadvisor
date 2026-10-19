@echo off
setlocal
call "%~dp0common.cmd"
call "%~dp0install-check.cmd"
if errorlevel 1 exit /b 1

echo ==================================================
echo        Mangadvisor - Restart complet
echo ==================================================
echo.

pushd "%ROOT_DIR%"
rem Ne pas laisser tourner l'ancien site Streamlit apres un restart.
%COMPOSE_CMD% --profile legacy stop ui
if errorlevel 1 (
    popd
    endlocal
    exit /b 1
)
%COMPOSE_CMD% down
if errorlevel 1 (
    popd
    endlocal
    exit /b 1
)

%COMPOSE_CMD% up --build
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%