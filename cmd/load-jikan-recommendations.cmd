@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

echo ==================================================
echo    Mangadvisor - Load Jikan Recommendations
echo ==================================================
echo.
echo Projet : %ROOT_DIR%
echo.

echo --------------------------------------------------
echo Verification PostgreSQL
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
echo 1/2 - Creation table manga_recommendation_edge
echo --------------------------------------------------

docker exec -i mangadvisor_postgres psql -U manga -d mangadvisor < sql\schema\006_add_jikan_recommendation_tables.sql

if errorlevel 1 (
    echo.
    echo ERREUR : echec creation table recommendations.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo 2/2 - Chargement recommandations Jikan
echo --------------------------------------------------

python pipelines\engine\scripts\load_jikan_recommendations_to_postgres.py --reset

if errorlevel 1 (
    echo.
    echo ERREUR : echec chargement recommandations Jikan.
    pause
    exit /b 1
)

echo.
echo --------------------------------------------------
echo Controle final
echo --------------------------------------------------

docker exec -it mangadvisor_postgres psql -U manga -d mangadvisor -c "SELECT COUNT(*) AS nb_edges FROM manga_recommendation_edge;"

docker exec -it mangadvisor_postgres psql -U manga -d mangadvisor -c "SELECT m.title AS source, e.recommended_title, e.votes, rm.title AS linked_catalog_title FROM manga_recommendation_edge e JOIN manga m ON m.id = e.source_manga_id LEFT JOIN manga rm ON rm.id = e.recommended_manga_id ORDER BY e.votes DESC NULLS LAST, m.title ASC LIMIT 20;"

echo.
echo Chargement recommandations termine.
echo.
pause

endlocal