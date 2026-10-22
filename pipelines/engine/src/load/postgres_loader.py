"""
Module de chargement PostgreSQL pour Mangadvisor.

Rôle :
    - ouvrir une connexion PostgreSQL
    - charger des enregistrements Jikan en batch
    - faire un upsert sur mal_id
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


def local_database_settings(env_file: Path | None = None) -> dict[str, str]:
    """Read only database settings from the local .env for Windows CLI pipelines.

    Docker sets process environment variables and always takes precedence.
    The file is never modified and its secrets are not logged. Values with
    ordinary single/double-quote wrappers are accepted.
    """
    path = env_file or Path(__file__).resolve().parents[4] / ".env"
    if not path.is_file():
        return {}
    fields = {"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT"}
    found: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in fields:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        found[key] = value
    return found


def get_postgres_connection() -> Connection:
    """
    Ouvre une connexion PostgreSQL à partir des variables d'environnement.

    Variables attendues :
    - POSTGRES_DB
    - POSTGRES_USER
    - POSTGRES_PASSWORD
    - POSTGRES_HOST
    - POSTGRES_PORT
    """
    local = local_database_settings()
    # Respect Docker/CI env first; host is always explicit or localhost on Windows.
    dbname = os.getenv("POSTGRES_DB") or local.get("POSTGRES_DB", "mangadvisor")
    user = os.getenv("POSTGRES_USER") or local.get("POSTGRES_USER", "manga")
    password = os.getenv("POSTGRES_PASSWORD") or local.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD absent : renseigne le fichier .env.")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT") or local.get("POSTGRES_PORT", "5432")

    conn = psycopg.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        row_factory=dict_row,
    )
    return conn


def upsert_jikan_manga_batch(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """
    Charge un batch de mangas Jikan dans PostgreSQL avec upsert sur mal_id.

    Paramètres
    ----------
    conn : Connection
        Connexion PostgreSQL active.
    rows : list[dict[str, Any]]
        Lignes à charger.

    Retour
    ------
    int
        Nombre de lignes traitées.
    """
    if not rows:
        return 0

    sql = """
    INSERT INTO jikan_manga_source (
        source_name,
        mal_id,
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
        manga_type,
        genres_json,
        themes_json,
        demographics_json,
        authors_json,
        serializations_json,
        raw_json
    )
    VALUES (
        %(source_name)s,
        %(mal_id)s,
        %(title)s,
        %(title_english)s,
        %(title_japanese)s,
        %(synopsis)s,
        %(status)s,
        %(chapters)s,
        %(volumes)s,
        %(score)s,
        %(popularity)s,
        %(rank)s,
        %(members)s,
        %(favorites)s,
        %(published_from)s,
        %(published_to)s,
        %(manga_type)s,
        %(genres_json)s,
        %(themes_json)s,
        %(demographics_json)s,
        %(authors_json)s,
        %(serializations_json)s,
        %(raw_json)s
    )
    ON CONFLICT (mal_id)
    DO UPDATE SET
        source_name = EXCLUDED.source_name,
        title = COALESCE(NULLIF(BTRIM(EXCLUDED.title), ''), jikan_manga_source.title),
        title_english = COALESCE(NULLIF(BTRIM(EXCLUDED.title_english), ''), jikan_manga_source.title_english),
        title_japanese = COALESCE(NULLIF(BTRIM(EXCLUDED.title_japanese), ''), jikan_manga_source.title_japanese),
        synopsis = COALESCE(NULLIF(BTRIM(EXCLUDED.synopsis), ''), jikan_manga_source.synopsis),
        status = COALESCE(NULLIF(BTRIM(EXCLUDED.status), ''), jikan_manga_source.status),
        chapters = COALESCE(EXCLUDED.chapters, jikan_manga_source.chapters),
        volumes = COALESCE(EXCLUDED.volumes, jikan_manga_source.volumes),
        score = COALESCE(EXCLUDED.score, jikan_manga_source.score),
        popularity = COALESCE(EXCLUDED.popularity, jikan_manga_source.popularity),
        rank = COALESCE(EXCLUDED.rank, jikan_manga_source.rank),
        members = COALESCE(EXCLUDED.members, jikan_manga_source.members),
        favorites = COALESCE(EXCLUDED.favorites, jikan_manga_source.favorites),
        published_from = COALESCE(EXCLUDED.published_from, jikan_manga_source.published_from),
        published_to = COALESCE(EXCLUDED.published_to, jikan_manga_source.published_to),
        manga_type = COALESCE(NULLIF(BTRIM(EXCLUDED.manga_type), ''), jikan_manga_source.manga_type),
        genres_json = CASE WHEN EXCLUDED.genres_json IS NULL OR EXCLUDED.genres_json = '[]'::jsonb
            THEN jikan_manga_source.genres_json ELSE EXCLUDED.genres_json END,
        themes_json = CASE WHEN EXCLUDED.themes_json IS NULL OR EXCLUDED.themes_json = '[]'::jsonb
            THEN jikan_manga_source.themes_json ELSE EXCLUDED.themes_json END,
        demographics_json = CASE WHEN EXCLUDED.demographics_json IS NULL OR EXCLUDED.demographics_json = '[]'::jsonb
            THEN jikan_manga_source.demographics_json ELSE EXCLUDED.demographics_json END,
        authors_json = CASE WHEN EXCLUDED.authors_json IS NULL OR EXCLUDED.authors_json = '[]'::jsonb
            THEN jikan_manga_source.authors_json ELSE EXCLUDED.authors_json END,
        serializations_json = CASE WHEN EXCLUDED.serializations_json IS NULL OR EXCLUDED.serializations_json = '[]'::jsonb
            THEN jikan_manga_source.serializations_json ELSE EXCLUDED.serializations_json END,
        raw_json = COALESCE(jikan_manga_source.raw_json, '{}'::jsonb) ||
            jsonb_strip_nulls(EXCLUDED.raw_json),
        inserted_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    conn.commit()
    return len(rows)