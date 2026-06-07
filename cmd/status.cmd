@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo         Mangadvisor - Etat des services
echo ==================================================
echo.

pushd "%ROOT_DIR%"
%COMPOSE_CMD% ps

echo.
echo ==================================================
echo           Containers Docker actifs
echo ==================================================
echo.

docker ps --filter "name=mangadvisor"
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%