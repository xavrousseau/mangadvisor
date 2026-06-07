@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

REM ==================================================
REM Parametres catalogue Jikan
REM ==================================================
set "START_PAGE=1"
set "END_PAGE=10"
set "LIMIT=25"
set "SLEEP_SECONDS=1"

echo ==================================================
echo        Mangadvisor - Run Jikan Catalog
echo ==================================================
echo.
echo Projet       : %ROOT_DIR%
echo Pages        : %START_PAGE% a %END_PAGE%
echo Limit        : %LIMIT%
echo Sleep        : %SLEEP_SECONDS%s
echo.

echo --------------------------------------------------
echo Verification Docker / PostgreSQL
echo --------------------------------------------------

docker ps --filter "name=mangadvisor_postgres" --format "{{.Names}}" | findstr /I "mangadvisor_postgres" >nul

if errorlevel 1 (
    echo.
    echo ERREUR : le conteneur mangadvisor_postgres ne semble pas demarre.
    echo Lance d'abord la stack avec mangadvisor.cmd ou docker compose.
    echo.
    pause
    exit /b 1
)

echo OK : PostgreSQL est demarre.
echo.

echo --------------------------------------------------
echo 1/6 - Extraction Jikan SEARCH
echo --------------------------------------------------

python pipelines\engine\scripts\extract_jikan.py ^
    --mode search ^
    --start-page %START_PAGE% ^
    --end-page %END_PAGE% ^
    --limit %LIMIT% ^
    --order-by popularity ^
    --sort asc ^
    --sfw true ^
    --sleep-seconds %SLEEP_SECONDS% ^
    --force

if errorlevel 1 (
    echo.
    echo ERREUR : echec extraction Jikan SEARCH.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 2/6 - Extraction Jikan TOP
echo --------------------------------------------------

python pipelines\engine\scripts\extract_jikan.py ^
    --mode top ^
    --start-page %START_PAGE% ^
    --end-page %END_PAGE% ^
    --limit %LIMIT% ^
    --sleep-seconds %SLEEP_SECONDS% ^
    --force

if errorlevel 1 (
    echo.
    echo ERREUR : echec extraction Jikan TOP.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 3/6 - Nettoyage table source jikan_manga_source
echo --------------------------------------------------

docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor -c "TRUNCATE TABLE jikan_manga_source;"

if errorlevel 1 (
    echo.
    echo ERREUR : impossible de vider jikan_manga_source.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 4/6 - Chargement PostgreSQL search + top
echo --------------------------------------------------

python pipelines\engine\scripts\load_jikan_to_postgres.py --sources search top

if errorlevel 1 (
    echo.
    echo ERREUR : echec chargement Jikan vers PostgreSQL.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 5/6 - Reconstruction catalogue canonique
echo --------------------------------------------------

echo.
echo 5.1 - Reconstruction manga / genre / manga_genre
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\003_build_canonical_from_jikan.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec script 003_build_canonical_from_jikan.sql.
    pause
    exit /b 1
)

echo.
echo 5.2 - Creation theme / demographic si necessaire
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\004_add_theme_demographic_tables.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec script 004_add_theme_demographic_tables.sql.
    pause
    exit /b 1
)

echo.
echo 5.3 - Reconstruction theme / demographic
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\005_build_theme_demographic_from_jikan.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec script 005_build_theme_demographic_from_jikan.sql.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 6/6 - Controle final
echo --------------------------------------------------

docker exec -it mangadvisor_postgres psql -U manga -d mangadvisor -c "SELECT 'jikan_manga_source' AS table_name, COUNT(*) FROM jikan_manga_source UNION ALL SELECT 'manga', COUNT(*) FROM manga UNION ALL SELECT 'genre', COUNT(*) FROM genre UNION ALL SELECT 'manga_genre', COUNT(*) FROM manga_genre UNION ALL SELECT 'theme', COUNT(*) FROM theme UNION ALL SELECT 'manga_theme', COUNT(*) FROM manga_theme UNION ALL SELECT 'demographic', COUNT(*) FROM demographic UNION ALL SELECT 'manga_demographic', COUNT(*) FROM manga_demographic;"

if errorlevel 1 (
    echo.
    echo ERREUR : echec controle final.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo Catalogue Jikan reconstruit avec succes.
echo ==================================================
echo.
pause

endlocal