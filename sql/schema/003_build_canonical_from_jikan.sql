-- ==============================================================
-- Mangadvisor — safe, ADDITIVE canonical update from Jikan.
--
-- NEVER truncate manga or genre: user_manga_library, manga_fr_edition,
-- recommendation edges and book history reference stable manga IDs.
-- Each refresh updates canonical fields for existing MAL IDs and adds new
-- ones, keeping all user relationships intact.
--
-- IMPORTANT: old links are retained if Jikan removes a tag. The catalog
-- sync is intentionally additive until source-attributed tag provenance
-- enables safe targeted cleanup. This is not an exact replacement rebuild.
-- ==============================================================
BEGIN;

INSERT INTO manga (
    source_name, source_mal_id, title, title_english, title_japanese,
    synopsis, status, chapters, volumes, score, popularity, rank,
    members, favorites, published_from, published_to, manga_type
)
SELECT
    source_name, mal_id, title, title_english, title_japanese,
    synopsis, status, chapters, volumes, score, popularity, rank,
    members, favorites, published_from, published_to, manga_type
FROM jikan_manga_source
WHERE NULLIF(BTRIM(title), '') IS NOT NULL
ON CONFLICT (source_mal_id) DO UPDATE SET
    -- Preserve manga.id, all existing user associations and other sources.
    source_name = EXCLUDED.source_name,
    title = COALESCE(NULLIF(BTRIM(EXCLUDED.title), ''), manga.title),
    title_english = COALESCE(NULLIF(BTRIM(EXCLUDED.title_english), ''), manga.title_english),
    title_japanese = COALESCE(NULLIF(BTRIM(EXCLUDED.title_japanese), ''), manga.title_japanese),
    synopsis = COALESCE(EXCLUDED.synopsis, manga.synopsis),
    status = COALESCE(EXCLUDED.status, manga.status),
    chapters = COALESCE(EXCLUDED.chapters, manga.chapters),
    volumes = COALESCE(EXCLUDED.volumes, manga.volumes),
    score = COALESCE(EXCLUDED.score, manga.score),
    popularity = COALESCE(EXCLUDED.popularity, manga.popularity),
    rank = COALESCE(EXCLUDED.rank, manga.rank),
    members = COALESCE(EXCLUDED.members, manga.members),
    favorites = COALESCE(EXCLUDED.favorites, manga.favorites),
    published_from = COALESCE(EXCLUDED.published_from, manga.published_from),
    published_to = COALESCE(EXCLUDED.published_to, manga.published_to),
    manga_type = COALESCE(EXCLUDED.manga_type, manga.manga_type),
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO genre (name)
SELECT DISTINCT genre_item ->> 'name'
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.genres_json, '[]'::jsonb)
) AS genre_item
WHERE genre_item ->> 'name' IS NOT NULL
  AND BTRIM(genre_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

INSERT INTO manga_genre (manga_id, genre_id)
SELECT DISTINCT m.id, g.id
FROM jikan_manga_source j
JOIN manga m ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.genres_json, '[]'::jsonb)
) AS genre_item
JOIN genre g ON g.name = genre_item ->> 'name'
ON CONFLICT DO NOTHING;

COMMIT;

SELECT 'jikan_manga_source' AS table_name, COUNT(*) FROM jikan_manga_source
UNION ALL SELECT 'manga', COUNT(*) FROM manga
UNION ALL SELECT 'genre', COUNT(*) FROM genre
UNION ALL SELECT 'manga_genre', COUNT(*) FROM manga_genre;
