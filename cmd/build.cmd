@echo off
setlocal
call "%~dp0common.cmd"
call "%~dp0install-check.cmd"
if errorlevel 1 exit /b 1

echo ==================================================
echo            Mangadvisor - Build images
echo ==================================================
echo.

pushd "%ROOT_DIR%"
%COMPOSE_CMD% build
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%