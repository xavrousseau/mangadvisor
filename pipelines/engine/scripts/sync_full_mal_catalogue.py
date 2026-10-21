"""Synchronisation exhaustive du catalogue public MAL au format Jikan via Tenrai.

Le service PUBLIC Jikan a fermé en octobre 2026. La source actuelle est
https://api.tenrai.org/v1, compatible avec les fiches MAL/Jikan.

- /manga *sans q, type, sfw, genre, score ou statut*, tri MAL ID asc
- pagination réelle jusqu'à has_next_page=false, limite de sécurité 20000
- fichier de cache atomique par page / identité de la requête
- reprise par cache vérifié et upsert par lot dans jikan_manga_source
- PAS de rebuild destructeur ni de modification de user_manga_*.
- La consolidation de manga/genres/themes se fait APRES succès via SQL 003/005.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from pipelines.engine.scripts.load_jikan_to_postgres import transform_jikan_item
from pipelines.engine.src.load.postgres_loader import get_postgres_connection, upsert_jikan_manga_batch

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "jikan" / "complete_tenrai"
LOGS = ROOT / "data" / "logs" / "catalogue_complete"
DEFAULT_BASE = "https://api.tenrai.org/v1"
LIMIT = 100
MAX_PAGES = 20_000
CACHE_VERSION = 1


class CatalogueError(ValueError):
    pass


def base_url() -> str:
    base = os.environ.get("MANGA_API_BASE_URL", DEFAULT_BASE).strip().rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CatalogueError("L'API manga doit utiliser une URL HTTPS valide")
    if parsed.hostname == "api.jikan.moe":
        raise CatalogueError("Jikan public a fermé le 01/10/2026 ; utiliser Tenrai ou une instance compatible")
    if not parsed.path.endswith("/v1") and not parsed.path.endswith("/v4"):
        raise CatalogueError("URL API inattendue : utiliser /v1 ou /v4")
    return base


def query(page: int) -> dict:
    # The absent sfw flag is intentional: do not silently omit titles.
    return {"page": page, "limit": LIMIT, "order_by": "mal_id", "sort": "asc"}


def pagination(payload: Any, page: int) -> tuple[int, bool, int | None]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise CatalogueError(f"page {page} : data[] manquant")
    info = payload.get("pagination")
    if not isinstance(info, dict):
        raise CatalogueError(f"page {page} : pagination manquante")
    last, has_more = info.get("last_visible_page"), info.get("has_next_page")
    current = info.get("current_page")
    if not isinstance(last, int) or isinstance(last, bool) or last < page:
        raise CatalogueError(f"page {page} : pagination incohérente")
    if not isinstance(has_more, bool) or (has_more != (page < last)):
        raise CatalogueError(f"page {page} : fin de catalogue incohérente")
    if current is not None and current != page:
        raise CatalogueError(f"page {page} : current_page inattendu")
    items = payload.get("data")
    if not items or len(items) > LIMIT:
        raise CatalogueError(f"page {page} : page vide ou dépasse {LIMIT} notices")
    ids = [x.get("mal_id") for x in items if isinstance(x, dict)]
    if (len(ids) != len(items) or
            any(not isinstance(i, int) or isinstance(i, bool) or i <= 0 for i in ids) or
            len(set(ids)) != len(ids)):
        raise CatalogueError(f"page {page} : identifiants MAL manquants ou doublonnés")
    if ids != sorted(ids):
        raise CatalogueError(f"page {page} : ordre MAL ID instable, arrêt de sécurité")
    total = info.get("items")
    expected = total.get("total") if isinstance(total, dict) else None
    if expected is not None and (not isinstance(expected, int) or expected < len(items)):
        expected = None
    return last, has_more, expected


def cache_path(page: int) -> Path:
    return RAW / f"manga_page_{page:05d}.json"


def load_cache(page: int, base: str) -> dict | None:
    path = cache_path(page)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if (value.get("mangadvisor_source") != "tenrai" or
                value.get("mangadvisor_api_base") != base or
                value.get("mangadvisor_query") != query(page)):
            return None
        pagination(value, page)
        return value
    except (ValueError, OSError, TypeError, KeyError):
        return None


def persist(page: int, base: str, payload: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    path = cache_path(page)
    tmp = path.with_suffix(".json.tmp")
    value = {**payload, "mangadvisor_source": "tenrai",
             "mangadvisor_api_base": base, "mangadvisor_query": query(page),
             "mangadvisor_cache_version": CACHE_VERSION}
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def retrieve(session: requests.Session, base: str, page: int, *,
             pause: float = 1.1, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            response = session.get(base + "/manga", params=query(page), timeout=35)
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt + 1 >= retries:
                    response.raise_for_status()
                raw_retry = response.headers.get("Retry-After", "")
                try:
                    requested = max(0.0, min(float(raw_retry), 120.0))
                except (TypeError, ValueError):
                    requested = 0.0
                duration = max(requested, 3 * 2**attempt, pause)
                print(f"API {response.status_code} page {page} ; délai {duration:.0f}s", flush=True)
                time.sleep(duration)
                continue
            response.raise_for_status()
            data = response.json()
            pagination(data, page)
            return data
        except (requests.RequestException, ValueError) as exc:
            if attempt + 1 >= retries:
                raise CatalogueError(f"page {page} : échec après {retries} tentatives : {exc}") from exc
            duration = max(3 * 2**attempt, pause)
            print(f"Problème temporaire page {page} ; délai {duration:.0f}s", flush=True)
            time.sleep(duration)
    raise CatalogueError(f"page {page} : impossible d'obtenir une réponse")


def normalized_rows(payload: dict) -> list[dict]:
    rows = []
    for data in payload["data"]:
        row = transform_jikan_item(data)
        if row is None or not isinstance(row.get("title"), str) or not row["title"].strip():
            raise CatalogueError("Notice sans titre/id valide : ne pas déclarer le lot complet")
        row["source_name"] = "tenrai"
        rows.append(row)
    return rows


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(data: dict) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    path = LOGS / "last_sync.json"
    tmp = LOGS / "last_sync.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def run(*, plan: bool = False, refresh: bool = False, max_pages: int = MAX_PAGES,
        batch_pages: int = 20, pause: float = 1.1,
        session: requests.Session | None = None, connection_factory=get_postgres_connection) -> dict:
    if not 1 <= max_pages <= MAX_PAGES:
        raise CatalogueError("max_pages doit être compris entre 1 et 20000")
    if not 1 <= batch_pages <= 50 or pause < 1.0:
        raise CatalogueError("lot entre 1-50 pages, pause >= 1 seconde")
    base = base_url()
    session = session or requests.Session()
    # Always refresh page 1: the source's total/last page may have changed.
    first = retrieve(session, base, 1, pause=pause)
    total_pages, _, expected = pagination(first, 1)
    report = {"provider": base, "source": "tenrai_mal_jikan_compatible",
              "catalogue_scope": "ALL_PUBLIC_SEARCH_NO_SFW_NO_TYPE_FILTER",
              "status": "PLAN" if plan else "RUNNING",
              "source_total_reported": expected,
              "source_pages_reported": total_pages,
              "max_pages": max_pages, "page_size": LIMIT,
              "started_at": now(), "pages_processed": 0,
              "pages_fetched": 0, "pages_cached": 0,
              "source_rows_processed": 0, "unique_ids_in_run": 0,
              "db_upserts": 0, "complete": False,
              "canonical_synced": False}
    if plan:
        return report
    persist(1, base, first)
    seen: set[int] = set()
    page_rows = []
    db = connection_factory()
    try:
        for page in range(1, min(total_pages, max_pages) + 1):
            if page == 1:
                payload = first
                report["pages_fetched"] += 1
            else:
                cached = None if refresh else load_cache(page, base)
                if cached:
                    payload = cached
                    report["pages_cached"] += 1
                else:
                    time.sleep(pause)
                    payload = retrieve(session, base, page, pause=pause)
                    persist(page, base, payload)
                    report["pages_fetched"] += 1
            last, has_next, _ = pagination(payload, page)
            if page > last or (page != 1 and not has_next and page != total_pages):
                raise CatalogueError(f"page {page} : pagination modifiée pendant le parcours")
            rows = normalized_rows(payload)
            for row in rows:
                mal_id = row["mal_id"]
                if mal_id in seen:
                    raise CatalogueError(f"MAL ID {mal_id} dupliqué entre pages : recherche instable")
                seen.add(mal_id)
            page_rows.extend(rows)
            report["pages_processed"] = page
            report["source_rows_processed"] += len(rows)
            if page % batch_pages == 0 or page == min(total_pages, max_pages):
                # PostgreSQL jikan_manga_source only, by MAL ID.
                report["db_upserts"] += upsert_jikan_manga_batch(db, page_rows)
                report["unique_ids_in_run"] = len(seen)
                page_rows.clear()
                write_status(report)
                print(f"Pages {page}/{total_pages} ; MAL uniques {len(seen)} ; "
                      f"source SQL {report['db_upserts']} ; cache {report['pages_cached']}", flush=True)
        if total_pages > max_pages:
            report["status"] = "INCOMPLETE_PAGE_CAP"
            write_status(report)
            raise CatalogueError(
                f"Source : {total_pages} pages, plafond {max_pages}. "
                "Aucune consolidation canonique : reprendre avec plafond augmenté.")
        if expected is not None and len(seen) != expected:
            report["status"] = "INCOMPLETE_TOTAL_MISMATCH"
            write_status(report)
            raise CatalogueError(
                f"Source annonce {expected} mangas, mais {len(seen)} IDs récupérés. "
                "Vérifier la pagination/les filtres ; aucune consolidation canonique.")
        report["status"] = "SOURCE_COMPLETE_PENDING_CANONICAL_SQL"
        report["complete"] = True
        report["completed_at"] = now()
        write_status(report)
        return report
    except Exception as exc:
        if report["status"] == "RUNNING":
            report["status"] = "INTERRUPTED"
            report["error_type"] = type(exc).__name__
            write_status(report)
        raise
    finally:
        db.close()


def finalize() -> dict:
    """Mark completion ONLY after canonical SQL 003/005 was actually applied."""
    status_path = LOGS / "last_sync.json"
    if not status_path.is_file():
        raise CatalogueError("Synchronisation source non commencée")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if not status.get("complete") or status.get("status") not in (
            "SOURCE_COMPLETE_PENDING_CANONICAL_SQL", "CATALOGUE_COMPLETE"):
        raise CatalogueError("Les pages source ne sont pas toutes récupérées")
    with get_postgres_connection() as db, db.cursor() as cur:
        cur.execute("""SELECT COUNT(*) AS n FROM jikan_manga_source j
                      LEFT JOIN manga m ON m.source_mal_id = j.mal_id
                      WHERE m.id IS NULL""")
        missing = cur.fetchone()["n"]
        if missing:
            raise CatalogueError(f"{missing} œuvres MAL non synchronisées dans manga")
        cur.execute("""SELECT
          (SELECT COUNT(*) FROM jikan_manga_source) AS source_count,
          (SELECT COUNT(*) FROM manga) AS canonical_count,
          (SELECT COUNT(*) FROM manga_genre) AS genre_links,
          (SELECT COUNT(*) FROM manga_theme) AS theme_links""")
        counts = cur.fetchone()
    if counts["source_count"] < status["unique_ids_in_run"]:
        raise CatalogueError("Le nombre de références source en base est trop faible")
    if counts["canonical_count"] < status["unique_ids_in_run"]:
        raise CatalogueError("Le catalogue canonique est plus petit que l'échantillon collecté")
    status.update({
        "canonical_synced": True, "status": "CATALOGUE_COMPLETE",
        "finalized_at": now(), "db_counts": dict(counts)})
    write_status(status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Catalogue MAL/Jikan complet via Tenrai, progressif et reprenable")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Compter les pages sans écrire PostgreSQL")
    mode.add_argument("--finalize", action="store_true", help="Valider les compteurs APRES scripts SQL 003/005")
    parser.add_argument("--refresh", action="store_true", help="Retélécharger les pages déjà en cache")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    parser.add_argument("--batch-pages", type=int, default=20)
    parser.add_argument("--pause", type=float, default=1.1)
    args = parser.parse_args(argv)
    try:
        if args.finalize:
            print(json.dumps(finalize(), ensure_ascii=False, indent=2))
            return 0
        data = run(plan=args.plan, refresh=args.refresh, max_pages=args.max_pages,
                   batch_pages=args.batch_pages, pause=args.pause)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (CatalogueError, requests.RequestException) as exc:
        print("Synchronisation non complète :", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
