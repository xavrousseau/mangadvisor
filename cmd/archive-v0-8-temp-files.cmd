@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "ARCHIVE_DIR=_archive\v0_8_13_cleanup"
set "BACKUP_DIR=%ARCHIVE_DIR%\backups"
set "TOOLS_DIR=%ARCHIVE_DIR%\tools_patches"
set "REPORTS_DIR=%ARCHIVE_DIR%\old_reports"

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%"

echo ==================================================
echo   Mangadvisor - Archivage fichiers temporaires
echo ==================================================
echo.
echo Projet  : %ROOT_DIR%
echo Archive : %ARCHIVE_DIR%
echo.

echo --------------------------------------------------
echo 1/3 - Archivage des fichiers .bak
echo --------------------------------------------------

for %%F in (
    "apps\api\app\main.py.bak*"
    "apps\ui\app\app.py.bak*"
    "pipelines\engine\scripts\*.bak*"
) do (
    for %%G in (%%F) do (
        if exist "%%~G" (
            echo Deplacement : %%~G
            git mv "%%~G" "%BACKUP_DIR%\" 2>nul
            if errorlevel 1 move "%%~G" "%BACKUP_DIR%\"
        )
    )
)

echo.
echo --------------------------------------------------
echo 2/3 - Archivage des scripts de patch temporaires
echo --------------------------------------------------

for %%F in (
    "tools\patch_*.py"
    "tools\fix_*.py"
) do (
    for %%G in (%%F) do (
        if exist "%%~G" (
            echo Deplacement : %%~G
            git mv "%%~G" "%TOOLS_DIR%\" 2>nul
            if errorlevel 1 move "%%~G" "%TOOLS_DIR%\"
        )
    )
)

echo.
echo --------------------------------------------------
echo 3/3 - Archivage des anciens rapports
echo --------------------------------------------------

for %%F in (
    "docs\reports\library_recommendation_tests_v0_8_1.md"
    "docs\reports\library_recommendation_tests_v0_8_2.md"
    "docs\reports\library_status_tests_v0_8_4.md"
    "docs\reports\recommendation_profile_tests_v0_6.md"
    "docs\reports\recommendation_profile_tests_v0_7_1.md"
    "docs\reports\recommendation_profile_tests_v0_7_2.md"
    "docs\reports\recommendation_profile_tests_v0_7_3.md"
    "docs\reports\recommendation_profile_tests_v0_8_0.md"
) do (
    if exist "%%~F" (
        echo Deplacement : %%~F
        git mv "%%~F" "%REPORTS_DIR%\" 2>nul
        if errorlevel 1 move "%%~F" "%REPORTS_DIR%\"
    )
)

echo.
echo ==================================================
echo Archivage termine.
echo ==================================================
echo.
echo Controle maintenant :
echo   git status --short
echo.
pause

endlocal