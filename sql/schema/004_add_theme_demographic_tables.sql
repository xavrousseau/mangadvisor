-- ==================================================
-- Mangadvisor
-- Ajout des tables canoniques Theme et Demographic
-- ==================================================

CREATE TABLE IF NOT EXISTS theme (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS manga_theme (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    theme_id INTEGER NOT NULL REFERENCES theme(id) ON DELETE CASCADE,
    PRIMARY KEY (manga_id, theme_id)
);

CREATE TABLE IF NOT EXISTS demographic (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS manga_demographic (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    demographic_id INTEGER NOT NULL REFERENCES demographic(id) ON DELETE CASCADE,
    PRIMARY KEY (manga_id, demographic_id)
);

CREATE INDEX IF NOT EXISTS idx_theme_name
    ON theme(name);

CREATE INDEX IF NOT EXISTS idx_demographic_name
    ON demographic(name);

CREATE INDEX IF NOT EXISTS idx_manga_theme_manga_id
    ON manga_theme(manga_id);

CREATE INDEX IF NOT EXISTS idx_manga_demographic_manga_id
    ON manga_demographic(manga_id);