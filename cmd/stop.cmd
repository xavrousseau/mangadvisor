@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo         Mangadvisor - Stop des services
echo ==================================================
echo.

pushd "%ROOT_DIR%"
%COMPOSE_CMD% stop
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%