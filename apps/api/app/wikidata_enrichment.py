"""Safe, incremental, CC0 Wikidata enrichment keyed ONLY by MyAnimeList manga ID.

P4087 identifies the exact MAL manga entry (not an anime's P4086 ID).
French-language Wikidata labels are *not* proof of a French publisher title.
This module does not create editions, ratings, user library entries, tags in
canonical tables, or AI-invented plot descriptions.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from apps.api.app.bnf_batch import connect_database

SOURCE = "WIKIDATA_P4087"
ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; metadata enrichment)"
DEFAULT_BATCH = 8
MAX_BATCH = 15
MAX_ROWS = 500
MAX_RESPONSE_BYTES = 1_000_000
REQUEST_TIMEOUT = 25
QID = re.compile(r"^Q[1-9][0-9]{0,11}$")
ENTITY_URL = re.compile(r"^https?://www\.wikidata\.org/entity/(Q[1-9][0-9]{0,11})$")
MAL_ID = re.compile(r"^[1-9][0-9]{0,8}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_wikidata_fact (
    manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
    source_mal_id INTEGER NOT NULL,
    wikidata_id TEXT NOT NULL CHECK (wikidata_id ~ '^Q[1-9][0-9]*$'),
    label_fr TEXT,
    description_fr TEXT,
    genres_fr TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
    source_name TEXT NOT NULL DEFAULT 'WIKIDATA_P4087',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS manga_wikidata_attempt (
    manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('MATCHED','NOT_FOUND','AMBIGUOUS','ERROR')),
    match_count INTEGER NOT NULL DEFAULT 0 CHECK (match_count >= 0),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_manga_wikidata_attempt_checked
    ON manga_wikidata_attempt(checked_at);
"""


class WikidataLookupError(Exception):
    """Public query service unavailable, invalid or truncated."""


def ensure_wikidata_schema(factory: Callable[..., Any]) -> None:
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


WORK_SQL = """
SELECT m.id, m.source_mal_id, m.title,
       CASE
         WHEN EXISTS (SELECT 1 FROM user_manga_inventory_declaration d
                      WHERE d.manga_id=m.id) THEN 0
         WHEN EXISTS (SELECT 1 FROM user_manga_library l
                      WHERE l.manga_id=m.id) THEN 1
         ELSE 2
       END AS priority
FROM manga m
LEFT JOIN manga_wikidata_attempt a ON a.manga_id=m.id
WHERE m.source_mal_id > 0
  AND COALESCE(m.manga_type,'Manga') IN ('Manga','Manhwa','Manhua','One-shot')
  AND (%(refresh)s OR a.checked_at IS NULL OR a.checked_at <
       NOW() - CASE WHEN a.status='ERROR' THEN INTERVAL '1 day'
                    ELSE INTERVAL '45 days' END)
ORDER BY priority ASC, m.popularity ASC NULLS LAST, m.id ASC
LIMIT %(limit)s
"""


def sparql_for_ids(ids: list[int]) -> str:
    if not ids or len(ids) > MAX_BATCH or any(
        type(value) is not int or not MAL_ID.fullmatch(str(value)) for value in ids
    ):
        raise ValueError("Invalid MyAnimeList manga identifiers.")
    literal_ids = " ".join('"' + str(value) + '"' for value in sorted(set(ids)))
    return (
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX schema: <http://schema.org/>\n"
        "SELECT ?malId ?item ?labelFr ?descriptionFr ?genreFr WHERE {\n"
        f"  VALUES ?malId {{ {literal_ids} }}\n"
        "  ?item wdt:P4087 ?malId .\n"
        '  OPTIONAL { ?item rdfs:label ?labelFr FILTER(LANG(?labelFr)="fr") }\n'
        '  OPTIONAL { ?item schema:description ?descriptionFr FILTER(LANG(?descriptionFr)="fr") }\n'
        "  OPTIONAL { ?item wdt:P136 ?genre . "
        '?genre rdfs:label ?genreFr FILTER(LANG(?genreFr)="fr") }\n'
        "}\nORDER BY ?malId ?item\n"
        f"LIMIT {MAX_ROWS}"
    )


def fetch_wikidata(ids: list[int]) -> dict[str, Any]:
    """One bounded GET request; never loop or retry when throttled (429)."""
    sparql = sparql_for_ids(ids)
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": sparql, "format": "json"})
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        # In particular: no automatic retries for 429 or 503. Caller records
        # ERROR and a later run may retry after the persisted cool-down.
        raise WikidataLookupError("Service Wikidata indisponible.") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise WikidataLookupError("Reponse Wikidata trop grande : lot refuse.")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise WikidataLookupError("Reponse Wikidata JSON invalide.") from exc


def _binding(row: dict[str, Any], name: str) -> str:
    part = row.get(name)
    if not isinstance(part, dict) or not isinstance(part.get("value"), str):
        return ""
    return part["value"]


def normalize_wikidata(
    requested_ids: list[int], data: dict[str, Any]
) -> dict[int, dict[str, Any]]:
    """Reject unknown MAL IDs and classify >1 Wikidata entities as ambiguous."""
    if not isinstance(data, dict):
        raise WikidataLookupError("Reponse Wikidata incoherente.")
    bindings = data.get("results", {}).get("bindings") if isinstance(data.get("results"), dict) else None
    if not isinstance(bindings, list) or len(bindings) >= MAX_ROWS:
        raise WikidataLookupError("Resultats Wikidata absents ou tronques.")
    wanted = set(requested_ids)
    matched: dict[int, dict[str, dict[str, Any]]] = {key: {} for key in wanted}
    for raw in bindings:
        if not isinstance(raw, dict):
            continue
        mal = _binding(raw, "malId")
        url = _binding(raw, "item")
        if not MAL_ID.fullmatch(mal) or int(mal) not in wanted:
            continue
        entity = ENTITY_URL.fullmatch(url)
        if not entity:
            continue
        mid = int(mal)
        qid = entity.group(1)
        entry = matched[mid].setdefault(
            qid, {"wikidata_id": qid, "label_fr": None,
                  "description_fr": None, "genres_fr": set()}
        )
        label = _binding(raw, "labelFr").strip()
        description = _binding(raw, "descriptionFr").strip()
        genre = _binding(raw, "genreFr").strip()
        if label and len(label) <= 200:
            entry["label_fr"] = label
        if description and len(description) <= 500:
            entry["description_fr"] = description
        if genre and len(genre) <= 120:
            entry["genres_fr"].add(genre)
    result = {}
    for mid, entities in matched.items():
        if len(entities) != 1:
            result[mid] = {"status": "AMBIGUOUS" if entities else "NOT_FOUND",
                           "match_count": len(entities), "fact": None}
            continue
        fact = next(iter(entities.values()))
        fact["genres_fr"] = sorted(fact["genres_fr"], key=str.casefold)[:12]
        result[mid] = {"status": "MATCHED", "match_count": 1, "fact": fact}
    return result


UPSERT_FACT_SQL = """
INSERT INTO manga_wikidata_fact
(manga_id,source_mal_id,wikidata_id,label_fr,description_fr,genres_fr,source_name,checked_at)
VALUES (%(manga_id)s,%(source_mal_id)s,%(wikidata_id)s,
        %(label_fr)s,%(description_fr)s,%(genres_fr)s,%(source_name)s,NOW())
ON CONFLICT (manga_id) DO UPDATE SET
  source_mal_id=EXCLUDED.source_mal_id,
  wikidata_id=EXCLUDED.wikidata_id,
  label_fr=EXCLUDED.label_fr,
  description_fr=EXCLUDED.description_fr,
  genres_fr=EXCLUDED.genres_fr,
  source_name=EXCLUDED.source_name,
  checked_at=NOW()
"""

UPSERT_ATTEMPT_SQL = """
INSERT INTO manga_wikidata_attempt(manga_id,status,match_count,checked_at)
VALUES (%(manga_id)s,%(status)s,%(match_count)s,NOW())
ON CONFLICT (manga_id) DO UPDATE SET
  status=EXCLUDED.status,match_count=EXCLUDED.match_count,checked_at=NOW()
"""


def run_batch(
    factory: Callable[..., Any],
    *, limit: int = DEFAULT_BATCH,
    refresh: bool = False,
    lookup: Callable[[list[int]], dict[str, Any]] = fetch_wikidata,
    target_ids: list[int] | None = None,
) -> dict[str, int]:
    """One independent, resumable batch; an unavailable provider fails visibly."""
    if not 1 <= limit <= MAX_BATCH:
        raise ValueError(f"Nombre de mangas : entre 1 et {MAX_BATCH}.")
    if target_ids is not None and (len(target_ids) > 250 or any(
        type(mid) is not int or mid <= 0 for mid in target_ids
    )):
        raise ValueError("Liste de mangas lies invalide ou trop longue.")
    ensure_wikidata_schema(factory)
    query = WORK_SQL
    params: dict[str, Any] = {"limit": limit, "refresh": refresh}
    if target_ids is not None:
        query = WORK_SQL.replace(
            "ORDER BY priority ASC", "  AND m.id=ANY(%(target_ids)s)\nORDER BY priority ASC"
        )
        params["target_ids"] = target_ids
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            works = list(cur.fetchall())
        conn.commit()
    counts = {"selected": len(works), "matched": 0, "not_found": 0,
              "ambiguous": 0, "error": 0, "labels_fr": 0, "genres_fr": 0}
    if not works:
        return counts
    ids = [int(row["source_mal_id"]) for row in works]
    try:
        results = normalize_wikidata(ids, lookup(ids))
    except (WikidataLookupError, TimeoutError, OSError, ValueError):
        results = {mal: {"status": "ERROR", "match_count": 0, "fact": None}
                   for mal in ids}

    with factory() as conn:
        for row in works:
            mid = int(row["source_mal_id"])
            outcome = results[mid]
            state = outcome["status"]
            with conn.transaction():
                with conn.cursor() as cur:
                    if state == "MATCHED":
                        fact = outcome["fact"]
                        cur.execute(UPSERT_FACT_SQL, {
                            "manga_id": row["id"],
                            "source_mal_id": mid,
                            "wikidata_id": fact["wikidata_id"],
                            "label_fr": fact["label_fr"],
                            "description_fr": fact["description_fr"],
                            "genres_fr": fact["genres_fr"],
                            "source_name": SOURCE,
                        })
                        counts["labels_fr"] += int(bool(fact["label_fr"]))
                        counts["genres_fr"] += len(fact["genres_fr"])
                    cur.execute(UPSERT_ATTEMPT_SQL, {
                        "manga_id": row["id"],
                        "status": state,
                        "match_count": outcome["match_count"],
                    })
            counts[state.lower()] += 1
            print(f"Manga {row['id']} (MAL {mid}) : {state}", flush=True)
    return counts


def create_wikidata_router(factory: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/enrichment", tags=["Wikidata CC0"])

    @router.get("/mangas/{manga_id}/wikidata")
    def wikidata_information(manga_id: int) -> dict[str, Any]:
        if manga_id <= 0:
            raise HTTPException(status_code=422, detail="Identifiant manga incorrect.")
        with factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%(id)s", {"id": manga_id})
                if cur.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Manga introuvable.")
                cur.execute(
                    """SELECT a.status, a.checked_at,
                              f.wikidata_id, f.label_fr, f.description_fr,
                              f.genres_fr, f.source_name
                       FROM manga_wikidata_attempt a
                       JOIN manga m ON m.id=a.manga_id
                       LEFT JOIN manga_wikidata_fact f
                         ON f.manga_id=m.id
                        AND f.source_mal_id=m.source_mal_id
                        AND a.status='MATCHED'
                       WHERE a.manga_id=%(id)s""",
                    {"id": manga_id},
                )
                stored = cur.fetchone()
        status = stored["status"] if stored else "NOT_SEARCHED"
        qid = stored.get("wikidata_id") if stored and status == "MATCHED" else None
        if qid and not QID.fullmatch(qid):
            qid = None
        return {
            "manga_id": manga_id,
            "status": status,
            "match_basis": "exact_mal_manga_id_P4087" if qid else None,
            "wikidata_id": qid,
            "source_name": SOURCE if qid else None,
            "source_url": ("https://www.wikidata.org/wiki/" + qid) if qid else None,
            "label_fr": stored.get("label_fr") if qid else None,
            "description_fr": stored.get("description_fr") if qid else None,
            "genres_fr": stored.get("genres_fr") if qid else [],
            "checked_at": stored["checked_at"].isoformat() if stored else None,
            "description_is_plot_synopsis": False,
            "french_publisher_title_verified": False,
            "editions_verified": False,
        }

    return router


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wikidata: libelles FR et genres lies au MAL ID.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_BATCH:
        parser.error(f"--limit doit etre entre 1 et {MAX_BATCH}")
    print("Wikidata : metadonnees CC0, rapprochement par MAL manga ID (P4087).")
    print("Les libelles FR ne prouvent pas une edition francaise commercialisee.")
    stats = run_batch(connect_database, limit=args.limit, refresh=args.refresh)
    print("Bilan : " + ", ".join(f"{k}={v}" for k, v in stats.items()), flush=True)
    if stats["selected"] and stats["error"] == stats["selected"]:
        print("ECHEC : Wikidata indisponible. Aucune donnee personnelle modifiee.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
