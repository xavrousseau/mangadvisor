-- ==================================================
-- Mangadvisor
-- V0.7 - Tables recommandations communautaires Jikan
-- ==================================================

CREATE TABLE IF NOT EXISTS manga_recommendation_edge (
    source_manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,

    recommended_mal_id INTEGER NOT NULL,
    recommended_manga_id INTEGER REFERENCES manga(id) ON DELETE SET NULL,
    recommended_title TEXT,

    votes INTEGER,
    raw_json JSONB,

    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (source_manga_id, recommended_mal_id)
);

CREATE INDEX IF NOT EXISTS idx_manga_reco_edge_source
    ON manga_recommendation_edge(source_manga_id);

CREATE INDEX IF NOT EXISTS idx_manga_reco_edge_recommended_mal_id
    ON manga_recommendation_edge(recommended_mal_id);

CREATE INDEX IF NOT EXISTS idx_manga_reco_edge_recommended_manga_id
    ON manga_recommendation_edge(recommended_manga_id);

CREATE INDEX IF NOT EXISTS idx_manga_reco_edge_votes
    ON manga_recommendation_edge(votes);