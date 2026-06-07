@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo      Mangadvisor - Rebuild Canonical Catalog
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

echo --------------------------------------------------
echo 1/3 - Reconstruction manga / genre / manga_genre
echo --------------------------------------------------
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\003_build_canonical_from_jikan.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec du script 003_build_canonical_from_jikan.sql
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 2/3 - Creation theme / demographic si necessaire
echo --------------------------------------------------
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\004_add_theme_demographic_tables.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec du script 004_add_theme_demographic_tables.sql
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 3/3 - Reconstruction theme / demographic
echo --------------------------------------------------
docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\005_build_theme_demographic_from_jikan.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec du script 005_build_theme_demographic_from_jikan.sql
    exit /b 1
)

echo.
echo ==================================================
echo Catalogue canonique reconstruit avec succes
echo ==================================================
echo.

docker exec -it mangadvisor_postgres psql -U manga -d mangadvisor -c "SELECT 'jikan_manga_source' AS table_name, COUNT(*) FROM jikan_manga_source UNION ALL SELECT 'manga', COUNT(*) FROM manga UNION ALL SELECT 'genre', COUNT(*) FROM genre UNION ALL SELECT 'manga_genre', COUNT(*) FROM manga_genre UNION ALL SELECT 'theme', COUNT(*) FROM theme UNION ALL SELECT 'manga_theme', COUNT(*) FROM manga_theme UNION ALL SELECT 'demographic', COUNT(*) FROM demographic UNION ALL SELECT 'manga_demographic', COUNT(*) FROM manga_demographic;"

echo.
pause
endlocal