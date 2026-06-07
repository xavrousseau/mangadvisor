-- Nombre total de mangas chargés
SELECT COUNT(*) AS total_mangas
FROM jikan_manga_source;

-- Aperçu rapide
SELECT
    id,
    mal_id,
    title,
    status,
    score,
    popularity
FROM jikan_manga_source
ORDER BY id
LIMIT 20;

-- Top mangas par score
SELECT
    mal_id,
    title,
    score,
    popularity
FROM jikan_manga_source
WHERE score IS NOT NULL
ORDER BY score DESC, popularity ASC
LIMIT 20;