-- ==================================================
-- Mangadvisor
-- Schéma canonique minimal V1
-- ==================================================

-- ==================================================
-- Table canonique : manga
-- ==================================================
-- Cette table représente l'entité métier principale.
-- Pour l'instant, elle est alimentée uniquement depuis Jikan.
-- ==================================================

CREATE TABLE IF NOT EXISTS manga (
    id SERIAL PRIMARY KEY,

    -- origine de la ligne canonique
    source_name TEXT NOT NULL DEFAULT 'jikan',
    source_mal_id INTEGER NOT NULL UNIQUE,

    -- titres
    title TEXT NOT NULL,
    title_english TEXT,
    title_japanese TEXT,

    -- description
    synopsis TEXT,

    -- métadonnées principales
    status TEXT,
    chapters INTEGER,
    volumes INTEGER,
    score NUMERIC(5,2),
    popularity INTEGER,
    rank INTEGER,
    members INTEGER,
    favorites INTEGER,

    -- publication
    published_from TIMESTAMP NULL,
    published_to TIMESTAMP NULL,

    -- type / format
    manga_type TEXT,

    -- suivi technique
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================
-- Table des genres
-- ==================================================
-- Liste distincte des genres extraits des données source.
-- ==================================================

CREATE TABLE IF NOT EXISTS genre (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- ==================================================
-- Table de liaison manga <-> genre
-- ==================================================
-- Relation n-n entre manga et genre.
-- ==================================================

CREATE TABLE IF NOT EXISTS manga_genre (
    manga_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,

    PRIMARY KEY (manga_id, genre_id),

    CONSTRAINT fk_manga_genre_manga
        FOREIGN KEY (manga_id)
        REFERENCES manga (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_manga_genre_genre
        FOREIGN KEY (genre_id)
        REFERENCES genre (id)
        ON DELETE CASCADE
);

-- ==================================================
-- Index utiles
-- ==================================================

CREATE INDEX IF NOT EXISTS idx_manga_title
    ON manga (title);

CREATE INDEX IF NOT EXISTS idx_manga_status
    ON manga (status);

CREATE INDEX IF NOT EXISTS idx_manga_score
    ON manga (score);

CREATE INDEX IF NOT EXISTS idx_manga_popularity
    ON manga (popularity);

CREATE INDEX IF NOT EXISTS idx_genre_name
    ON genre (name);