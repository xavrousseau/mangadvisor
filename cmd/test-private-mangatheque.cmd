@echo off
setlocal EnableExtensions
call "%~dp0common.cmd"
cd /d "%ROOT_DIR%"
echo ==================================================
echo   MANGADVISOR - AUDIT PRIVE DE TA MANGATHEQUE
echo ==================================================
echo.
echo Lecture seule : aucune importation ni modification des tomes.
echo Le fichier personnel reste dans private-evaluations (ignore par Git).
echo.
set "CSV_FILE=%~1"
if not defined CSV_FILE set /p "CSV_FILE=Chemin complet du CSV telecharge : "
set "CSV_FILE=%CSV_FILE:"=%"
if not exist "%CSV_FILE%" (
  echo [ERREUR] CSV introuvable : %CSV_FILE%
  exit /b 1
)
if not exist "%ROOT_DIR%\private-evaluations" mkdir "%ROOT_DIR%\private-evaluations"
copy /Y "%CSV_FILE%" "%ROOT_DIR%\private-evaluations\reference.csv" >nul
if errorlevel 1 (
  echo [ERREUR] Impossible de copier le fichier dans le repertoire prive.
  exit /b 1
)
echo Controle des correspondances et recommandations sur TON API locale...
%COMPOSE_CMD% exec -T api python cmd/evaluate-private-library.py --csv private-evaluations/reference.csv --out private-evaluations/results --url http://127.0.0.1:8000
if errorlevel 1 (
  echo [ERREUR] Controle impossible. Demarrer d'abord Mangadvisor avec l'option 3.
  exit /b 1
)
echo.
echo Rapports :
echo  %ROOT_DIR%\private-evaluations\results\rapport_collection_privee.json
echo  %ROOT_DIR%\private-evaluations\results\correspondances_collection_privee.csv
echo Ces fichiers ne sont jamais envoyes sur GitHub.
exit /b 0
