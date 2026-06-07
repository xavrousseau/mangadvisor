@echo off
setlocal

call "%~dp0common.cmd"

echo ==================================================
echo         Mangadvisor - Run Jikan Pipeline
echo ==================================================
echo.

call "%~dp0install-check.cmd"
if errorlevel 1 exit /b 1

REM Variables PostgreSQL pour le script Python
set "POSTGRES_DB=mangadvisor"
set "POSTGRES_USER=manga"
set "POSTGRES_PASSWORD=manga"
set "POSTGRES_HOST=localhost"
set "POSTGRES_PORT=5432"

REM Paramètres par défaut
set "START_PAGE=1"
set "END_PAGE=1"
set "LIMIT=25"
set "RESET_FLAG="

REM Lecture des arguments
:parse_args
if "%~1"=="" goto run_pipeline

if /I "%~1"=="--reset-db" (
    set "RESET_FLAG=--reset-db"
    shift
    goto parse_args
)

if /I "%~1"=="--start-page" (
    set "START_PAGE=%~2"
    shift
    shift
    goto parse_args
)

if /I "%~1"=="--end-page" (
    set "END_PAGE=%~2"
    shift
    shift
    goto parse_args
)

if /I "%~1"=="--limit" (
    set "LIMIT=%~2"
    shift
    shift
    goto parse_args
)

echo ERREUR : argument inconnu %~1
exit /b 1

:run_pipeline
echo Pages      : %START_PAGE% a %END_PAGE%
echo Limit      : %LIMIT%
if defined RESET_FLAG (
    echo Reset DB   : oui
) else (
    echo Reset DB   : non
)
echo.

pushd "%ROOT_DIR%"
python pipelines\engine\scripts\run_jikan_pipeline.py %RESET_FLAG% --start-page %START_PAGE% --end-page %END_PAGE% --limit %LIMIT%
set "RC=%ERRORLEVEL%"
popd

echo.
if %RC%==0 (
    echo ==================================================
    echo Pipeline Jikan termine avec succes
    echo ==================================================
) else (
    echo ==================================================
    echo ERREUR : echec du pipeline Jikan
    echo ==================================================
)

endlocal & exit /b %RC%