SELECT
    j.title,
    j.status,
    j.score,
    COALESCE(
        (
            SELECT STRING_AGG(g.item ->> 'name', ', ' ORDER BY g.item ->> 'name')
            FROM JSONB_ARRAY_ELEMENTS(j.genres_json) AS g(item)
        ),
        ''
    ) AS genres,
    COALESCE(
        (
            SELECT STRING_AGG(t.item ->> 'name', ', ' ORDER BY t.item ->> 'name')
            FROM JSONB_ARRAY_ELEMENTS(j.themes_json) AS t(item)
        ),
        ''
    ) AS themes,
    COALESCE(
        (
            SELECT STRING_AGG(d.item ->> 'name', ', ' ORDER BY d.item ->> 'name')
            FROM JSONB_ARRAY_ELEMENTS(j.demographics_json) AS d(item)
        ),
        ''
    ) AS demographics
FROM jikan_manga_source j
ORDER BY j.popularity
LIMIT 30;