-- ==================================================
-- Mangadvisor
-- V0.8 - Bibliothèque utilisateur
-- ==================================================

CREATE TABLE IF NOT EXISTS app_user (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO app_user (
    id,
    username,
    display_name
)
VALUES (
    1,
    'local_user',
    'Utilisateur local'
)
ON CONFLICT (id)
DO NOTHING;


CREATE TABLE IF NOT EXISTS user_manga_library (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,

    library_status TEXT NOT NULL CHECK (
        library_status IN (
            'OWNED',
            'READING',
            'READ',
            'WANT_TO_READ',
            'DROPPED',
            'NOT_INTERESTED'
        )
    ),

    user_score NUMERIC(3,1) CHECK (
        user_score IS NULL
        OR (
            user_score >= 0
            AND user_score <= 10
        )
    ),

    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,

    owned_volumes INTEGER CHECK (
        owned_volumes IS NULL
        OR owned_volumes >= 0
    ),

    read_volumes INTEGER CHECK (
        read_volumes IS NULL
        OR read_volumes >= 0
    ),

    notes TEXT,

    started_at DATE,
    finished_at DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_user_manga_library UNIQUE (user_id, manga_id)
);


CREATE INDEX IF NOT EXISTS idx_user_manga_library_user_id
    ON user_manga_library(user_id);

CREATE INDEX IF NOT EXISTS idx_user_manga_library_manga_id
    ON user_manga_library(manga_id);

CREATE INDEX IF NOT EXISTS idx_user_manga_library_status
    ON user_manga_library(library_status);

CREATE INDEX IF NOT EXISTS idx_user_manga_library_score
    ON user_manga_library(user_score);

CREATE INDEX IF NOT EXISTS idx_user_manga_library_favorite
    ON user_manga_library(is_favorite);


CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;

CREATE TRIGGER trg_app_user_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


DROP TRIGGER IF EXISTS trg_user_manga_library_updated_at ON user_manga_library;

CREATE TRIGGER trg_user_manga_library_updated_at
BEFORE UPDATE ON user_manga_library
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();