@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "REPORT_DIR=%ROOT_DIR%\docs\reports"
if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"

set "REPORT=%REPORT_DIR%\project_file_audit_v0_8_13.txt"

echo ================================================== > "%REPORT%"
echo   Mangadvisor - Audit fichiers projet V0.8.13 >> "%REPORT%"
echo ================================================== >> "%REPORT%"
echo. >> "%REPORT%"
echo Projet : %ROOT_DIR% >> "%REPORT%"
echo Date   : %DATE% %TIME% >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 1. Git status >> "%REPORT%"
echo ================================================== >> "%REPORT%"
git status --short >> "%REPORT%" 2>&1
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 2. Fichiers suivis par Git >> "%REPORT%"
echo ================================================== >> "%REPORT%"
git ls-files >> "%REPORT%" 2>&1
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 3. Fichiers non suivis par Git >> "%REPORT%"
echo ================================================== >> "%REPORT%"
git ls-files --others --exclude-standard >> "%REPORT%" 2>&1
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 4. Arborescence complete >> "%REPORT%"
echo ================================================== >> "%REPORT%"
tree /F /A >> "%REPORT%" 2>&1
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 5. Fichiers de sauvegarde / backup >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B *.bak *.backup *backup* 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 6. Scripts de patch / outils temporaires >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B tools\*.py 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 7. Scripts CMD >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B cmd\*.cmd 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 8. Rapports docs/reports >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B docs\reports\* 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 9. Fichiers Docker Compose >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B docker-compose*.yml compose*.yml 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo 10. Dossiers legacy >> "%REPORT%"
echo ================================================== >> "%REPORT%"
dir /S /B legacy 2>nul >> "%REPORT%"
echo. >> "%REPORT%"

echo ================================================== >> "%REPORT%"
echo Audit termine >> "%REPORT%"
echo ================================================== >> "%REPORT%"

echo.
echo Rapport genere :
echo %REPORT%
echo.
pause

endlocal