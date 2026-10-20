"""Read-only benchmark of specialized manga catalogue APIs on 50 real local titles.

Sources: Scrinis and MangaUpdates. No canonical/edition/library SQL writes.
Only local title strings are sent to these services (not ownership quantities,
notes or account identifiers). Output stays in gitignored data/logs.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from pipelines.engine.src.load.postgres_loader import get_postgres_connection

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "data" / "logs" / "catalog_sources"
SCRINIS_URL = "https://scrin.is/api/v1/search"
MANGAUPDATES_URL = "https://api.mangaupdates.com/v1/series/search"
MAX_ITEMS = 50
MAX_RESPONSE = 600_000
# Scrinis unauthenticated: 15 requests/minute. Stay strictly below.
DELAYS = {"scrinis": 4.5, "mangaupdates": 2.0}
USER_AGENT = "Mangadvisor/4.8 (https://github.com/xavrousseau/mangadvisor; read-only source evaluation)"


def title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", normalized, flags=re.UNICODE))


def select_samples(conn: Any, limit: int = MAX_ITEMS) -> list[dict[str, Any]]:
    """Prefer unresolved private inventory entries, then owned, then catalog.

    Source keys, status, personal quantities and notes are NEVER sent to APIs.
    SQL is read-only; the output holds title and a broad origin label only.
    """
    if not 1 <= limit <= MAX_ITEMS:
        raise ValueError("Échantillon autorisé : 1 à 50 œuvres")
    queries = [
        ("""SELECT COALESCE(NULLIF(TRIM(work_declared),''),entry_title) AS title,
                   NULL::TEXT AS title_english, NULL::TEXT AS title_japanese,
                   NULL::INTEGER AS mal_id
            FROM user_manga_inventory_pending
            WHERE user_id=1
            ORDER BY saved_at,source_key LIMIT %s""", "pending", min(25, limit)),
        ("""SELECT m.title,m.title_english,m.title_japanese,m.source_mal_id AS mal_id
            FROM user_manga_inventory_declaration d JOIN manga m ON m.id=d.manga_id
            WHERE d.user_id=1
            ORDER BY m.popularity ASC NULLS LAST,m.id LIMIT %s""", "owned", min(15, limit)),
        ("""SELECT m.title,m.title_english,m.title_japanese,m.source_mal_id AS mal_id
            FROM manga m ORDER BY m.popularity ASC NULLS LAST,m.id LIMIT %s""", "catalog", limit),
    ]
    sample: list[dict[str, Any]] = []
    seen: set[str] = set()
    with conn.cursor() as cur:
        for sql, origin, size in queries:
            if len(sample) >= limit:
                break
            cur.execute(sql, (size,))
            for entry in cur.fetchall():
                title = str(entry.get("title") or "").strip()
                key = title_key(title)
                if not key or key in seen:
                    continue
                seen.add(key)
                sample.append({
                    "title": title[:200],
                    "title_english": str(entry.get("title_english") or "")[:200],
                    "title_japanese": str(entry.get("title_japanese") or "")[:200],
                    "mal_id": entry.get("mal_id"),
                    "origin": origin,
                })
                if len(sample) >= limit:
                    break
    # A catalogue can be smaller than 50, but reports never pad with fake works.
    return sample


def candidates_from_payload(payload: Any) -> list[dict[str, Any]] | None:
    """Accept documented-style search wrappers, refuse unrecognized schemas.

    A malformed response is not a negative match. Never invent an entity.
    """
    if not isinstance(payload, dict):
        return None
    root: Any = None
    for key in ("results", "items", "series", "data"):
        if isinstance(payload.get(key), list):
            root = payload[key]
            break
        if isinstance(payload.get(key), dict):
            nested = payload[key]
            for inner in ("results", "items", "series", "data"):
                if isinstance(nested.get(inner), list):
                    root = nested[inner]
                    break
            if root is not None:
                break
    if root is None:
        return None
    candidates: list[dict[str, Any]] = []
    for item in root[:5]:
        if not isinstance(item, dict):
            continue
        obj = item.get("record") if isinstance(item.get("record"), dict) else item
        if isinstance(obj.get("series"), dict):
            obj = obj["series"]
        if not isinstance(obj, dict):
            continue
        title = obj.get("title") or obj.get("name") or obj.get("series_title")
        if isinstance(title, dict):
            title = title.get("fr") or title.get("en") or title.get("ja") or title.get("primary")
        if not isinstance(title, str) or not title.strip():
            continue
        identifier = obj.get("series_id") or obj.get("id") or obj.get("slug")
        aliases = obj.get("alternative_titles") or obj.get("aliases") or []
        if isinstance(aliases, dict):
            aliases = list(aliases.values())
        names = []
        for a in aliases if isinstance(aliases, list) else []:
            if isinstance(a, str):
                names.append(a)
            elif isinstance(a, dict):
                val = a.get("title") or a.get("name")
                if isinstance(val, str):
                    names.append(val)
        for k in ("title_fr", "title_en", "title_english", "original_title", "title_japanese"):
            if isinstance(obj.get(k), str):
                names.append(obj[k])
        mal_id = obj.get("mal_id") or obj.get("myanimelist_id")
        candidates.append({
            "title": title.strip()[:200],
            "aliases": names[:12],
            "id": identifier,
            "mal_id": mal_id,
            "has_isbn": bool(obj.get("isbn") or obj.get("isbns")),
            "has_genres": bool(obj.get("genres") or obj.get("categories") or obj.get("tags")),
        })
    return candidates


def classify(sample: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Candidate classifications are NEVER canonical manga identity proof."""
    known_names = [sample[k] for k in ("title", "title_english", "title_japanese") if sample.get(k)]
    keys = {title_key(x) for x in known_names}
    ranked = []
    for obj in candidates:
        options = [obj["title"], *obj.get("aliases", [])]
        normalized = [title_key(v) for v in options if v]
        matched_mal = (sample.get("mal_id") is not None and obj.get("mal_id") is not None
                       and str(sample["mal_id"]) == str(obj["mal_id"]))
        exact = any(x in keys for x in normalized if x)
        similarity = max((SequenceMatcher(None, left, right).ratio()
                         for left in keys for right in normalized if left and right), default=0.0)
        rank = 2 if matched_mal else 1 if exact else 0
        ranked.append((rank, round(similarity, 3), obj))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if not ranked:
        return {"status": "NO_MATCH", "candidate": None, "score": None}
    best = ranked[0]
    competitors = [x for x in ranked[1:] if x[0] == best[0] and abs(x[1] - best[1]) < 0.05]
    if competitors and best[0] >= 1:
        state = "AMBIGUOUS"
    elif best[0] == 2:
        state = "SAME_MAL_ID"
    elif best[0] == 1:
        state = "EXACT_TITLE"
    else:
        state = "SUGGESTION_ONLY"
    obj = best[2]
    return {"status": state, "score": best[1],
            "candidate": {"title": obj["title"], "id": obj["id"],
                          "mal_id": obj.get("mal_id"), "has_isbn": obj["has_isbn"],
                          "has_genres": obj["has_genres"]}}


def request_source(name: str, term: str, session: Any) -> dict[str, Any]:
    """One bounded public request per source/title, no silent reattempts."""
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if name == "scrinis":
        # Site quota without an API key is 15/min; caller enforces spacing.
        response = session.get(SCRINIS_URL, params={"q": term, "limit": 5},
                               headers=headers, timeout=20)
    elif name == "mangaupdates":
        response = session.post(MANGAUPDATES_URL,
                                json={"search": term, "perpage": 5},
                                headers=headers, timeout=20)
    else:
        raise ValueError("Source inconnue")
    if response.status_code in (401, 403, 429):
        return {"status": "UNAVAILABLE", "http_status": response.status_code}
    if response.status_code >= 400:
        return {"status": "HTTP_ERROR", "http_status": response.status_code}
    raw = response.content
    if len(raw) > MAX_RESPONSE:
        return {"status": "RESPONSE_TOO_LARGE"}
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return {"status": "INVALID_JSON"}
    extracted = candidates_from_payload(parsed)
    if extracted is None:
        return {"status": "UNKNOWN_SCHEMA"}
    return {"status": "OK", "candidates": extracted}


def compare_works(sample: list[dict[str, Any]], *, session=None, sleep=time.sleep,
                  providers=("scrinis", "mangaupdates")) -> dict[str, Any]:
    """Sequential quota-aware audit, with provider failures clearly distinguished."""
    session = session or requests.Session()
    entries = [{"title": row["title"], "origin": row["origin"],
                "sources": {}} for row in sample]
    disabled: set[str] = set()
    for provider in providers:
        last_request = None
        for sample_row, output in zip(sample, entries):
            if provider in disabled:
                output["sources"][provider] = {"status": "SKIPPED_PROVIDER_UNAVAILABLE"}
                continue
            if last_request is not None:
                elapsed = time.monotonic() - last_request
                sleep(max(0.0, DELAYS[provider] - elapsed))
            last_request = time.monotonic()
            try:
                result = request_source(provider, sample_row["title"], session)
            except (requests.RequestException, OSError) as exc:
                # Do not persist exception text, which may contain request headers.
                result = {"status": "NETWORK_ERROR", "error_type": type(exc).__name__}
            if result.get("status") == "OK":
                comparison = classify(sample_row, result["candidates"])
                output["sources"][provider] = comparison
            else:
                output["sources"][provider] = result
                if result["status"] == "UNAVAILABLE":
                    disabled.add(provider)
        print(f"[sources] {provider}: {dict(Counter(x['sources'][provider]['status'] for x in entries))}")
    aggregates = {
        provider: dict(Counter(row["sources"].get(provider, {}).get("status", "NOT_TESTED")
                               for row in entries))
        for provider in providers
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notice": ("Diagnostic exploratoire uniquement. Une suggestion ou un titre exact "
                   "ne prouve ni l'identite de l'oeuvre, ni l'edition francaise, "
                   "ni la possession d'un livre."),
        "sample_count": len(entries),
        "sample_by_origin": dict(Counter(s["origin"] for s in sample)),
        "providers": aggregates,
        "entries": entries,
    }


def save_report(report: dict[str, Any], folder: Path = REPORT_DIR) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    json_path = folder / f"comparatif_sources_{suffix}.json"
    csv_path = folder / f"comparatif_sources_{suffix}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "titre", "segment", "scrinis_etat", "scrinis_titre",
            "scrinis_isbn", "scrinis_genres", "mangaupdates_etat",
            "mangaupdates_titre", "mangaupdates_genres"])
        writer.writeheader()
        for entry in report["entries"]:
            a = entry["sources"].get("scrinis", {})
            b = entry["sources"].get("mangaupdates", {})
            ac, bc = a.get("candidate") or {}, b.get("candidate") or {}
            writer.writerow({
                "titre": entry["title"], "segment": entry["origin"],
                "scrinis_etat": a.get("status"), "scrinis_titre": ac.get("title"),
                "scrinis_isbn": ac.get("has_isbn"), "scrinis_genres": ac.get("has_genres"),
                "mangaupdates_etat": b.get("status"),
                "mangaupdates_titre": bc.get("title"),
                "mangaupdates_genres": bc.get("has_genres"),
            })
    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comparer Scrinis et MangaUpdates sur 50 mangas locaux")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true",
                        help="Voir les titres retenus ; aucun appel HTTP, aucun fichier")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_ITEMS:
        parser.error("La limite doit être comprise entre 1 et 50")
    with get_postgres_connection() as conn:
        sample = select_samples(conn, args.limit)
    if not sample:
        print("Aucun manga en base : comparatif non lance.")
        return 2
    print("Échantillon :", len(sample), "œuvres",
          dict(Counter(row["origin"] for row in sample)))
    if args.dry_run:
        for i, row in enumerate(sample, 1):
            print(f"{i:02d}. [{row['origin']}] {row['title']}")
        return 0
    print("Titres envoyés à Scrinis et MangaUpdates, sans données de lecture ou de possession.")
    print("Quotas respectés ; aucune écriture dans PostgreSQL.")
    result = compare_works(sample)
    paths = save_report(result)
    print("Résultats enregistrés localement :", *(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
