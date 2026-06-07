-- ==================================================
-- Mangadvisor
-- Schéma minimal pour stocker les données brutes Jikan
-- ==================================================

-- Extension utile pour la suite du projet
CREATE EXTENSION IF NOT EXISTS vector;

-- ==================================================
-- Table source : jikan_manga_source
-- ==================================================
-- Cette table stocke les mangas tels qu'ils proviennent de Jikan,
-- sans logique de consolidation multi-sources pour l'instant.
-- Elle sert de table source brute structurée.
-- ==================================================

CREATE TABLE IF NOT EXISTS jikan_manga_source (
    id SERIAL PRIMARY KEY,

    -- Identifiant du manga dans Jikan / MyAnimeList
    mal_id INTEGER NOT NULL UNIQUE,

    -- Titres
    title TEXT,
    title_english TEXT,
    title_japanese TEXT,

    -- Synopsis
    synopsis TEXT,

    -- Métadonnées principales
    status TEXT,
    chapters INTEGER,
    volumes INTEGER,
    score NUMERIC(5,2),
    popularity INTEGER,
    rank INTEGER,
    members INTEGER,
    favorites INTEGER,

    -- Dates
    published_from TIMESTAMP NULL,
    published_to TIMESTAMP NULL,

    -- Type / format
    manga_type TEXT,

    -- Genres et thèmes stockés en JSON pour garder la structure source
    genres_json JSONB,
    themes_json JSONB,
    demographics_json JSONB,
    authors_json JSONB,
    serializations_json JSONB,

    -- Réponse brute Jikan pour audit / debug / retraitement futur
    raw_json JSONB NOT NULL,

    -- Suivi technique
    source_name TEXT NOT NULL DEFAULT 'jikan',
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================
-- Index utiles
-- ==================================================

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_title
    ON jikan_manga_source (title);

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_status
    ON jikan_manga_source (status);

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_score
    ON jikan_manga_source (score);

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_popularity
    ON jikan_manga_source (popularity);

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_raw_json
    ON jikan_manga_source
    USING GIN (raw_json);

CREATE INDEX IF NOT EXISTS idx_jikan_manga_source_genres_json
    ON jikan_manga_source
    USING GIN (genres_json);