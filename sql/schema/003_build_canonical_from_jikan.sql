-- ==================================================
-- Mangadvisor
-- Construction du catalogue canonique depuis Jikan
-- ==================================================

-- Pour la V0.1, on reconstruit proprement les tables canoniques.
-- Plus tard, quand il y aura des utilisateurs, on évitera les TRUNCATE.
TRUNCATE TABLE manga_genre, genre, manga RESTART IDENTITY CASCADE;

-- ==================================================
-- 1. Alimentation de la table manga
-- ==================================================

INSERT INTO manga (
    source_name,
    source_mal_id,
    title,
    title_english,
    title_japanese,
    synopsis,
    status,
    chapters,
    volumes,
    score,
    popularity,
    rank,
    members,
    favorites,
    published_from,
    published_to,
    manga_type
)
SELECT
    source_name,
    mal_id AS source_mal_id,
    title,
    title_english,
    title_japanese,
    synopsis,
    status,
    chapters,
    volumes,
    score,
    popularity,
    rank,
    members,
    favorites,
    published_from,
    published_to,
    manga_type
FROM jikan_manga_source
WHERE title IS NOT NULL;

-- ==================================================
-- 2. Alimentation de la table genre
-- ==================================================

INSERT INTO genre (name)
SELECT DISTINCT
    genre_item ->> 'name' AS name
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.genres_json, '[]'::jsonb)
) AS genre_item
WHERE genre_item ->> 'name' IS NOT NULL
  AND BTRIM(genre_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

-- ==================================================
-- 3. Alimentation de la table de liaison manga_genre
-- ==================================================

INSERT INTO manga_genre (
    manga_id,
    genre_id
)
SELECT DISTINCT
    m.id AS manga_id,
    g.id AS genre_id
FROM jikan_manga_source j
JOIN manga m
    ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.genres_json, '[]'::jsonb)
) AS genre_item
JOIN genre g
    ON g.name = genre_item ->> 'name'
ON CONFLICT DO NOTHING;

-- ==================================================
-- 4. Contrôles rapides
-- ==================================================

SELECT 'jikan_manga_source' AS table_name, COUNT(*) FROM jikan_manga_source
UNION ALL
SELECT 'manga', COUNT(*) FROM manga
UNION ALL
SELECT 'genre', COUNT(*) FROM genre
UNION ALL
SELECT 'manga_genre', COUNT(*) FROM manga_genre;