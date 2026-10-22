"""Incremental BnF bibliography discovery for Mangadvisor.

This is an evidence queue, NOT an importer of confirmed manga editions.
Title search never proves a book belongs to a manga: candidate ISBNs remain
unverified until the user checks an ISBN through the existing collection flow.
No user library, reading progress, canonical manga or confirmed ISBN is written.
"""
from __future__ import annotations

import argparse
from functools import partial
import os
import re
import time
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException

from apps.api.app.collection import (
    BNF_SOURCE, EDITION_KINDS, isbn13_normalize, safe_bnf_ark,
)
from apps.api.app.edition_discovery import search_bnf_title_pages
from apps.api.app.edition_enrichment import select_search_titles, title_clue

SOURCE = "BNF_SRU"
MAX_BATCH = 25
DEFAULT_BATCH = 10
REQUEST_DELAY = 1.25
MAX_CANDIDATES_PER_MANGA = 120

# Additive and idempotent. Separate from manga_fr_edition by design.
# There is NO foreign-key insert into user_manga_volume or library tables.
SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_bnf_candidate (
  manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
  isbn13 VARCHAR(13) NOT NULL CHECK (isbn13 ~ '^[0-9]{13}$'),
  title_fr TEXT NOT NULL,
  author_fr TEXT,
  publisher_fr TEXT,
  release_date_text TEXT,
  language_recorded TEXT,
  edition_kind_suggested TEXT NOT NULL DEFAULT 'UNKNOWN',
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  searched_title TEXT NOT NULL,
  title_clue TEXT NOT NULL,
  title_clue_rank SMALLINT NOT NULL CHECK (title_clue_rank BETWEEN 0 AND 2),
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (manga_id, isbn13)
);
CREATE INDEX IF NOT EXISTS idx_manga_bnf_candidate_isbn
  ON manga_bnf_candidate(isbn13);
CREATE TABLE IF NOT EXISTS manga_bnf_attempt (
  manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('CHECKED','EMPTY','PARTIAL','ERROR','SKIPPED')),
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  candidate_count INTEGER NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
  searches_completed INTEGER NOT NULL DEFAULT 0 CHECK (searches_completed >= 0),
  searches_failed INTEGER NOT NULL DEFAULT 0 CHECK (searches_failed >= 0)
);
CREATE INDEX IF NOT EXISTS idx_manga_bnf_attempt_checked
  ON manga_bnf_attempt(checked_at);
"""


def connect_database():
    return psycopg.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        row_factory=dict_row,
        connect_timeout=10,
    )


def ensure_bnf_schema(connection_factory: Callable[..., Any]) -> None:
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


WORK_SQL = """
SELECT m.id, m.title, m.title_english,
       CASE
         WHEN EXISTS (SELECT 1 FROM user_manga_inventory_declaration d
                      WHERE d.manga_id=m.id) THEN 0
         WHEN EXISTS (SELECT 1 FROM user_manga_library l
                      WHERE l.manga_id=m.id) THEN 1
         ELSE 2
       END AS priority
FROM manga m
LEFT JOIN manga_bnf_attempt a ON a.manga_id=m.id
WHERE COALESCE(m.manga_type,'Manga') IN ('Manga','Manhwa','Manhua','One-shot')
  AND (%(refresh)s OR a.checked_at IS NULL OR a.checked_at <
       now() - CASE WHEN a.status IN ('ERROR','PARTIAL')
                    THEN INTERVAL '1 day' ELSE INTERVAL '45 days' END)
ORDER BY priority ASC, m.popularity ASC NULLS LAST, m.id ASC
LIMIT %(limit)s
"""


def normalize_candidates(
    titles: list[str],
    search_results: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Capture only source records with safe BnF provenance and validated ISBN.

    Title overlap is a UI hint, not a work-level match or automatic registration.
    """
    found: dict[str, dict[str, Any]] = {}
    for searched_title, payload in search_results:
        if not isinstance(payload, dict):
            continue
        for row in payload.get("items", []):
            if not isinstance(row, dict) or row.get("status") != "CANDIDATE_UNCONFIRMED":
                continue
            if row.get("manga_match_verified") is not False:
                continue
            try:
                isbn = isbn13_normalize(str(row.get("isbn13") or ""))
            except ValueError:
                continue
            ark = safe_bnf_ark(str(row.get("source_url") or ""))
            title = str(row.get("title_fr") or "").strip()[:350]
            if not ark or not title:
                continue
            source_url = "https://catalogue.bnf.fr/" + ark
            rank, clue = title_clue(title, titles)
            kind = row.get("edition_kind_suggested")
            if kind not in EDITION_KINDS:
                kind = "UNKNOWN"
            item = {
                "isbn13": isbn,
                "title_fr": title,
                "author_fr": str(row.get("author_fr") or "")[:350] or None,
                "publisher_fr": str(row.get("publisher_fr") or "")[:200] or None,
                "release_date_text": str(row.get("release_date_text") or "")[:80] or None,
                "language_recorded": str(row.get("language_recorded") or "")[:60] or None,
                "edition_kind_suggested": kind,
                "source_name": BNF_SOURCE,
                "source_url": source_url,
                "searched_title": searched_title,
                "title_clue": clue,
                "title_clue_rank": rank,
            }
            if isbn not in found or rank > found[isbn]["title_clue_rank"]:
                found[isbn] = item
    return sorted(
        found.values(),
        key=lambda item: (-item["title_clue_rank"], item["title_fr"].casefold(), item["isbn13"])
    )[:MAX_CANDIDATES_PER_MANGA]


UPSERT_CANDIDATE = """
INSERT INTO manga_bnf_candidate
(manga_id, isbn13, title_fr, author_fr, publisher_fr, release_date_text,
 language_recorded, edition_kind_suggested, source_name, source_url,
 searched_title, title_clue, title_clue_rank)
VALUES
(%(manga_id)s, %(isbn13)s, %(title_fr)s, %(author_fr)s, %(publisher_fr)s,
 %(release_date_text)s, %(language_recorded)s, %(edition_kind_suggested)s,
 %(source_name)s, %(source_url)s, %(searched_title)s, %(title_clue)s, %(title_clue_rank)s)
ON CONFLICT (manga_id, isbn13) DO UPDATE SET
  title_fr=EXCLUDED.title_fr,
  author_fr=EXCLUDED.author_fr,
  publisher_fr=EXCLUDED.publisher_fr,
  release_date_text=EXCLUDED.release_date_text,
  language_recorded=EXCLUDED.language_recorded,
  edition_kind_suggested=EXCLUDED.edition_kind_suggested,
  source_name=EXCLUDED.source_name,
  source_url=EXCLUDED.source_url,
  searched_title=EXCLUDED.searched_title,
  title_clue=EXCLUDED.title_clue,
  title_clue_rank=EXCLUDED.title_clue_rank,
  last_seen_at=now()
"""


def record_attempt(
    cur: Any, manga_id: int, status: str, count: int, completed: int, failed: int
) -> None:
    cur.execute(
        """INSERT INTO manga_bnf_attempt
           (manga_id,status,checked_at,candidate_count,searches_completed,searches_failed)
           VALUES (%(manga_id)s,%(status)s,now(),%(count)s,%(completed)s,%(failed)s)
           ON CONFLICT (manga_id) DO UPDATE SET
             status=EXCLUDED.status,checked_at=now(),
             candidate_count=EXCLUDED.candidate_count,
             searches_completed=EXCLUDED.searches_completed,
             searches_failed=EXCLUDED.searches_failed""",
        {"manga_id": manga_id, "status": status, "count": count,
         "completed": completed, "failed": failed},
    )


def run_batch(
    connection_factory: Callable[..., Any],
    *, limit: int = DEFAULT_BATCH,
    refresh: bool = False,
    search: Callable[[str], dict[str, Any]] = search_bnf_title_pages,
    sleep: Callable[[float], Any] = time.sleep,
    target_ids: list[int] | None = None,
) -> dict[str, int]:
    """One bounded, resumable batch. A successful work is checkpointed individually."""
    if not 1 <= limit <= MAX_BATCH:
        raise ValueError(f"Nombre de mangas : entre 1 et {MAX_BATCH}.")
    if target_ids is not None and (len(target_ids) > 250 or any(
        type(mid) is not int or mid <= 0 for mid in target_ids
    )):
        raise ValueError("Liste de mangas lies invalide ou trop longue.")
    ensure_bnf_schema(connection_factory)
    query = WORK_SQL
    params: dict[str, Any] = {"limit": limit, "refresh": refresh}
    if target_ids is not None:
        query = WORK_SQL.replace(
            "ORDER BY priority ASC", "  AND m.id=ANY(%(target_ids)s)\nORDER BY priority ASC"
        )
        params["target_ids"] = target_ids
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            works = list(cur.fetchall())
        conn.commit()

        stats = {"selected": len(works), "searched": 0, "candidates": 0,
                 "checked": 0, "empty": 0, "partial": 0, "error": 0, "skipped": 0}
        attempted_requests = 0
        for index, work in enumerate(works, start=1):
            titles = select_search_titles(work)
            results: list[tuple[str, dict[str, Any]]] = []
            errors = 0
            for title in titles:
                if attempted_requests:
                    sleep(REQUEST_DELAY)
                attempted_requests += 1
                try:
                    results.append((title, search(title)))
                except (HTTPException, TimeoutError, OSError, ValueError):
                    errors += 1
            candidates = normalize_candidates(titles, results)
            if not titles:
                status = "SKIPPED"
            elif errors == len(titles):
                status = "ERROR"
            elif errors or any(payload.get("page_limit_reached", False) for _, payload in results):
                status = "PARTIAL"
            else:
                status = "CHECKED" if candidates else "EMPTY"
            with conn.transaction():
                with conn.cursor() as cur:
                    for item in candidates:
                        cur.execute(UPSERT_CANDIDATE, {"manga_id": work["id"], **item})
                    record_attempt(cur, int(work["id"]), status,
                                   len(candidates), len(results), errors)
            stats["searched"] += len(results)
            stats["candidates"] += len(candidates)
            stats[status.lower()] += 1
            print(f"[{index}/{len(works)}] Manga {work['id']} : {status} ; "
                  f"{len(candidates)} notices candidates ; {errors} erreur(s).", flush=True)
    return stats


def create_bnf_catalog_router(connection_factory: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["BnF enrichissement progressif"])

    @router.get("/mangas/{manga_id}/bnf-candidates")
    def bnf_candidates(manga_id: int) -> dict[str, Any]:
        if manga_id < 1:
            raise HTTPException(status_code=422, detail="Identifiant manga incorrect.")
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%(id)s", {"id": manga_id})
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Manga introuvable.")
                cur.execute(
                    """SELECT status,checked_at,candidate_count
                       FROM manga_bnf_attempt WHERE manga_id=%(id)s""",
                    {"id": manga_id},
                )
                attempt = cur.fetchone()
                cur.execute(
                    """SELECT c.isbn13,c.title_fr,c.author_fr,c.publisher_fr,
                              c.release_date_text,c.language_recorded,
                              c.edition_kind_suggested,c.source_name,c.source_url,
                              c.title_clue,c.title_clue_rank,c.searched_title,
                              CASE
                                WHEN e.manga_id=%(id)s THEN 'REGISTERED_HERE'
                                WHEN e.manga_id IS NOT NULL THEN 'REGISTERED_OTHER'
                                ELSE 'TO_VERIFY'
                              END AS registration_status
                       FROM manga_bnf_candidate c
                       LEFT JOIN manga_fr_edition e ON e.isbn13=c.isbn13
                       WHERE c.manga_id=%(id)s
                       ORDER BY c.title_clue_rank DESC,c.title_fr ASC,c.isbn13 ASC
                       LIMIT 30""",
                    {"id": manga_id},
                )
                items = list(cur.fetchall())
        return {
            "manga_id": manga_id, "source": SOURCE,
            "candidate_only": True, "manga_match_verified": False,
            "status": attempt["status"] if attempt else "NOT_SEARCHED",
            "last_checked_at": attempt["checked_at"].isoformat() if attempt else None,
            "candidate_count": attempt["candidate_count"] if attempt else 0,
            "count": len(items), "items": items,
            "notice": "Résultats bibliographiques BnF non vérifiés pour cette série. "
                      "Valider l'ISBN via la fiche avant tout ajout.",
        }

    return router


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recherche BnF non destructive, par petits lots.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--pages", type=int, default=3,
                        help="Pages BnF par titre : 1 a 10 (plus de 3 : manga cible obligatoire).")
    parser.add_argument("--manga-id", type=int, default=None,
                        help="Limiter la recherche a un manga interne precis.")
    parser.add_argument("--refresh", action="store_true",
                        help="Rechercher même les mangas déjà analysés récemment.")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_BATCH:
        parser.error(f"--limit doit être entre 1 et {MAX_BATCH}")
    print("Mangadvisor : enrichissement BnF (candidats UNIQUEMENT).", flush=True)
    print("Ni la mangathèque, ni les éditions confirmées ne sont modifiées.", flush=True)
    if args.manga_id is not None and args.manga_id <= 0:
        parser.error("--manga-id doit etre un identifiant positif.")
    if not 1 <= args.pages <= 10:
        parser.error("--pages doit etre entre 1 et 10.")
    if args.pages > 3 and args.manga_id is None:
        parser.error("--pages superieur a 3 exige --manga-id pour limiter les appels BnF.")
    search = partial(search_bnf_title_pages, max_pages=args.pages)
    stats = run_batch(connect_database, limit=args.limit, refresh=args.refresh,
                      target_ids=[args.manga_id] if args.manga_id is not None else None,
                      search=search)
    print("Bilan :", ", ".join(f"{key}={value}" for key, value in stats.items()), flush=True)
    if stats["selected"] and stats["error"] == stats["selected"]:
        print("ECHEC : toutes les recherches BnF ont échoué. "
              "Aucune édition ni donnée personnelle n'a été modifiée.", flush=True)
        return 1
    print("Consulte les fiches mangas : les ISBN à vérifier sont affichés séparément.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
