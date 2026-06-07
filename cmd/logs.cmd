@echo off
setlocal
call "%~dp0common.cmd"

echo ==================================================
echo        Mangadvisor - Logs en temps reel
echo ==================================================
echo.
echo Pour quitter les logs : CTRL + C
echo.

pushd "%ROOT_DIR%"
%COMPOSE_CMD% logs -f
set "RC=%ERRORLEVEL%"
popd

endlocal & exit /b %RC%