"""
Module de chargement PostgreSQL pour Mangadvisor.

Rôle :
    - ouvrir une connexion PostgreSQL
    - charger des enregistrements Jikan en batch
    - faire un upsert sur mal_id
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


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
    dbname = os.getenv("POSTGRES_DB", "mangadvisor")
    user = os.getenv("POSTGRES_USER", "manga")
    password = os.getenv("POSTGRES_PASSWORD", "manga")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

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
        title = EXCLUDED.title,
        title_english = EXCLUDED.title_english,
        title_japanese = EXCLUDED.title_japanese,
        synopsis = EXCLUDED.synopsis,
        status = EXCLUDED.status,
        chapters = EXCLUDED.chapters,
        volumes = EXCLUDED.volumes,
        score = EXCLUDED.score,
        popularity = EXCLUDED.popularity,
        rank = EXCLUDED.rank,
        members = EXCLUDED.members,
        favorites = EXCLUDED.favorites,
        published_from = EXCLUDED.published_from,
        published_to = EXCLUDED.published_to,
        manga_type = EXCLUDED.manga_type,
        genres_json = EXCLUDED.genres_json,
        themes_json = EXCLUDED.themes_json,
        demographics_json = EXCLUDED.demographics_json,
        authors_json = EXCLUDED.authors_json,
        serializations_json = EXCLUDED.serializations_json,
        raw_json = EXCLUDED.raw_json,
        inserted_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    conn.commit()
    return len(rows)