-- ==================================================
-- Mangadvisor
-- Construction des thèmes et démographies depuis Jikan
-- ==================================================

TRUNCATE TABLE manga_theme, manga_demographic, theme, demographic RESTART IDENTITY CASCADE;

-- ==================================================
-- 1. Alimentation des thèmes
-- ==================================================

INSERT INTO theme (name)
SELECT DISTINCT
    theme_item ->> 'name' AS name
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.themes_json, '[]'::jsonb)
) AS theme_item
WHERE theme_item ->> 'name' IS NOT NULL
  AND BTRIM(theme_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

-- ==================================================
-- 2. Liaison manga / thème
-- ==================================================

INSERT INTO manga_theme (
    manga_id,
    theme_id
)
SELECT DISTINCT
    m.id AS manga_id,
    t.id AS theme_id
FROM jikan_manga_source j
JOIN manga m
    ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.themes_json, '[]'::jsonb)
) AS theme_item
JOIN theme t
    ON t.name = theme_item ->> 'name'
ON CONFLICT DO NOTHING;

-- ==================================================
-- 3. Alimentation des démographies
-- ==================================================

INSERT INTO demographic (name)
SELECT DISTINCT
    demographic_item ->> 'name' AS name
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.demographics_json, '[]'::jsonb)
) AS demographic_item
WHERE demographic_item ->> 'name' IS NOT NULL
  AND BTRIM(demographic_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

-- ==================================================
-- 4. Liaison manga / démographie
-- ==================================================

INSERT INTO manga_demographic (
    manga_id,
    demographic_id
)
SELECT DISTINCT
    m.id AS manga_id,
    d.id AS demographic_id
FROM jikan_manga_source j
JOIN manga m
    ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.demographics_json, '[]'::jsonb)
) AS demographic_item
JOIN demographic d
    ON d.name = demographic_item ->> 'name'
ON CONFLICT DO NOTHING;

-- ==================================================
-- 5. Contrôles rapides
-- ==================================================

SELECT 'theme' AS table_name, COUNT(*) FROM theme
UNION ALL
SELECT 'manga_theme', COUNT(*) FROM manga_theme
UNION ALL
SELECT 'demographic', COUNT(*) FROM demographic
UNION ALL
SELECT 'manga_demographic', COUNT(*) FROM manga_demographic;