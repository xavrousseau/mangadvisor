-- ==============================================================
-- Mangadvisor — NON-DESTRUCTIVE enrichment of themes/demographics.
-- Never TRUNCATE these tables: shared tags and manga links must survive.
-- Source-removed labels are retained until source provenance permits
-- reliable targeted cleanup without erasing user-annotated tags.
-- ==============================================================
BEGIN;

INSERT INTO theme (name)
SELECT DISTINCT theme_item ->> 'name'
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.themes_json, '[]'::jsonb)
) AS theme_item
WHERE theme_item ->> 'name' IS NOT NULL
  AND BTRIM(theme_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

INSERT INTO manga_theme (manga_id, theme_id)
SELECT DISTINCT m.id, t.id
FROM jikan_manga_source j
JOIN manga m ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.themes_json, '[]'::jsonb)
) AS theme_item
JOIN theme t ON t.name = theme_item ->> 'name'
ON CONFLICT DO NOTHING;

INSERT INTO demographic (name)
SELECT DISTINCT demographic_item ->> 'name'
FROM jikan_manga_source j
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.demographics_json, '[]'::jsonb)
) AS demographic_item
WHERE demographic_item ->> 'name' IS NOT NULL
  AND BTRIM(demographic_item ->> 'name') <> ''
ON CONFLICT (name) DO NOTHING;

INSERT INTO manga_demographic (manga_id, demographic_id)
SELECT DISTINCT m.id, d.id
FROM jikan_manga_source j
JOIN manga m ON m.source_mal_id = j.mal_id
CROSS JOIN LATERAL jsonb_array_elements(
    COALESCE(j.demographics_json, '[]'::jsonb)
) AS demographic_item
JOIN demographic d ON d.name = demographic_item ->> 'name'
ON CONFLICT DO NOTHING;

COMMIT;

SELECT 'theme' AS table_name, COUNT(*) FROM theme
UNION ALL SELECT 'manga_theme', COUNT(*) FROM manga_theme
UNION ALL SELECT 'demographic', COUNT(*) FROM demographic
UNION ALL SELECT 'manga_demographic', COUNT(*) FROM manga_demographic;
