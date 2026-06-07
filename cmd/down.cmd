@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo         Mangadvisor - Down de la stack
echo ==================================================
echo.

pushd "%ROOT_DIR%"
%COMPOSE_CMD% down
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%