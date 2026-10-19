@echo off
setlocal
call "%~dp0common.cmd"
if not exist "%ENV_FILE%" (
  echo ERREUR : fichier .env absent. Installer Mangadvisor d'abord.
  exit /b 1
)
if not exist "%ROOT_DIR%\data\private\inventaire.csv" (
  echo.
  echo Inventaire prive introuvable : data\private\inventaire.csv
  echo Decompresser le pack personnel fourni dans le dossier racine Mangadvisor.
  echo Ne jamais copier cet inventaire dans les tests publics de GitHub.
  exit /b 2
)
pushd "%ROOT_DIR%"
echo.
echo ============================================================
echo       AUDIT PRIVE DE LA MANGATHEQUE - LECTURE SEULE
echo ============================================================
echo Utilise le catalogue et le conseiller de la base LOCALE.
echo Aucune modification des ISBN, notes, volumes ou statuts.
echo Les rapprochements incertains ne sont jamais valides de force.
echo.
%COMPOSE_CMD% exec -T api python tests/local/private_inventory_audit.py --input data/private/inventaire.csv --report data/private/rapport_audit.json --api http://127.0.0.1:8000
set "CODE=%ERRORLEVEL%"
echo.
if "%CODE%"=="0" (
  echo RESULTAT : data\private\rapport_audit.json
  echo Le rapport reste sur ce PC et n'est pas envoye a GitHub.
) else (
  echo ERREUR : impossible de terminer l'audit. Verifier Docker et les messages.
)
popd
exit /b %CODE%
