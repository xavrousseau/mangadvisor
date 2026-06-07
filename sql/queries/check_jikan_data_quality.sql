-- ==================================================
-- Contrôles qualité de base sur jikan_manga_source
-- ==================================================

-- 1. Nombre total de lignes
SELECT COUNT(*) AS total_rows
FROM jikan_manga_source;

-- 2. Nombre de mal_id distincts
SELECT COUNT(DISTINCT mal_id) AS distinct_mal_id
FROM jikan_manga_source;

-- 3. Doublons éventuels sur mal_id
SELECT
    mal_id,
    COUNT(*) AS nb_rows
FROM jikan_manga_source
GROUP BY mal_id
HAVING COUNT(*) > 1
ORDER BY nb_rows DESC, mal_id ASC;

-- 4. Titres manquants
SELECT COUNT(*) AS missing_title
FROM jikan_manga_source
WHERE title IS NULL OR TRIM(title) = '';

-- 5. Synopsis manquants
SELECT COUNT(*) AS missing_synopsis
FROM jikan_manga_source
WHERE synopsis IS NULL OR TRIM(synopsis) = '';

-- 6. Score manquant
SELECT COUNT(*) AS missing_score
FROM jikan_manga_source
WHERE score IS NULL;

-- 7. Volumes négatifs ou incohérents
SELECT COUNT(*) AS invalid_volumes
FROM jikan_manga_source
WHERE volumes IS NOT NULL AND volumes < 0;

-- 8. Chapters négatifs ou incohérents
SELECT COUNT(*) AS invalid_chapters
FROM jikan_manga_source
WHERE chapters IS NOT NULL AND chapters < 0;

-- 9. Dates incohérentes
SELECT COUNT(*) AS invalid_published_range
FROM jikan_manga_source
WHERE published_from IS NOT NULL
  AND published_to IS NOT NULL
  AND published_from > published_to;

-- 10. Répartition par status
SELECT
    status,
    COUNT(*) AS nb_rows
FROM jikan_manga_source
GROUP BY status
ORDER BY nb_rows DESC;