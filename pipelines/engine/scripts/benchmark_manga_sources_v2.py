"""V2 read-only catalogue comparison with candidates, provenance and bounded details.

Never writes to manga/edition/inventory tables. Only title searches leave PC,
after an explicit confirmation in mangadvisor.cmd. Detailed external metadata
is exploratory evidence, not a verified physical edition or owned ISBN.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

from pipelines.engine.scripts import benchmark_manga_sources as v1
from pipelines.engine.scripts import catalogue_french_matching as fr_policy
from pipelines.engine.scripts.bnf_bulk_import import isbn13

REPORT_DIR = v1.REPORT_DIR
CACHE_DIR = REPORT_DIR / "cache_v2"
SOURCES = ("scrinis", "mangaupdates")
BASE = {"scrinis": "https://scrin.is/api/v1",
        "mangaupdates": "https://api.mangaupdates.com/v1"}
PAUSE = {"scrinis": 4.5, "mangaupdates": 2.0}
MAX_RESPONSE = 600_000
MAX_DETAIL_RESPONSE = 8_000_000
MAX_CANDIDATES = 8
DETAIL_BUDGET = 12
ALT_BUDGET = 6
EXPLICIT_ALIASES = {"City Hunter - Nicky Larson": "City Hunter",
                    "Adieu Eri": "Sayonara Eri"}
# This diagnostic only uses metadata from public APIs. Covers, copyright
# blurbs and full descriptions are not copied into its reports.

def names_from(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return list(dict.fromkeys(x for item in value for x in names_from(item)))[:30]
    if isinstance(value, dict):
        return names_from([value[k] for k in
                           ("title", "name", "fr", "en", "ja", "primary", "value", "text")
                           if k in value])
    return []


def pick_id(*objects: dict) -> str | None:
    # Scrinis search hits may wrap the series under "series" or "record".
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        for name in ("series_id", "id", "work_id", "hub_id"):
            value = obj.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                return str(value)
            if isinstance(value, str) and re.fullmatch(r"[1-9]\d{0,14}", value):
                return value
    return None


def hits_of(payload: Any) -> tuple[list[dict] | None, dict]:
    """Return search records and bounded, non-content diagnostics of API shape."""
    if isinstance(payload, list):
        return payload[:MAX_CANDIDATES], {"root_type": "list"}
    if not isinstance(payload, dict):
        return None, {"root_type": type(payload).__name__}
    diag = {"root_keys": sorted(payload.keys())[:20]}
    spaces = [payload]
    for key in ("data", "result", "payload"):
        if isinstance(payload.get(key), dict):
            spaces.append(payload[key])
    for obj in spaces:
        for key in ("results", "items", "series", "hits", "records", "data"):
            item = obj.get(key)
            if isinstance(item, list):
                diag["hit_key"] = key
                diag["example_keys"] = sorted(item[0].keys())[:25] if item and isinstance(item[0], dict) else []
                return item[:MAX_CANDIDATES], diag
    return None, diag


def parse_hits(payload: Any, *, source: str | None = None) -> tuple[list[dict] | None, dict]:
    hits, diagnostic = hits_of(payload)
    if hits is None:
        return None, diagnostic
    records = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        nested = [hit]
        for key in ("record", "series", "work", "entity", "result"):
            if isinstance(hit.get(key), dict):
                nested.insert(0, hit[key])
        obj = next((item for item in nested if
                    names_from(item.get("title") or item.get("name") or
                               item.get("series_title"))), None)
        if obj is None:
            continue
        titles = names_from(obj.get("title") or obj.get("name") or obj.get("series_title"))
        alts = names_from(obj.get("associated")) + names_from(obj.get("aliases"))
        alts += names_from(obj.get("alternative_titles"))
        for key in ("title_fr", "title_en", "title_english", "title_japanese",
                    "original_title", "titles", "original", "title_localized"):
            alts += names_from(obj.get(key))
        series_id = pick_id(obj, hit)
        if source == "scrinis":
            # Verified against /api/v1/series/9884 (public_n=9884,
            # hub_id=UUID). Never use the UUID in the numeric API route.
            for candidate in (obj, hit):
                public_n = candidate.get("public_n")
                if isinstance(public_n, int) and not isinstance(public_n, bool) and 0 < public_n < 10**14:
                    series_id = str(public_n)
                    break
        records.append({
            "id": series_id,
            "title": titles[0][:200],
            "aliases": list(dict.fromkeys(x[:200] for x in alts if x))[:18],
            "format": str(obj.get("type") or obj.get("format") or "")[:60],
            "mal_id": obj.get("mal_id") or obj.get("myanimelist_id"),
            "has_isbn_in_search": bool(obj.get("isbn") or obj.get("isbns")),
            "has_genres_in_search": bool(obj.get("genres") or obj.get("categories") or obj.get("tags")),
        })
    diagnostic["parsed"] = len(records)
    diagnostic["with_id"] = sum(bool(x["id"]) for x in records)
    # Log only types, never raw opaque supplier identifiers.
    if hits and isinstance(hits[0], dict):
        diagnostic["identity_field_types"] = {
            key: type(hits[0][key]).__name__
            for key in ("hub_id", "ids", "public_n") if key in hits[0]
        }
    return records, diagnostic


def rank(sample: dict, matches: list[dict]) -> dict:
    wanted = {v1.title_key(x) for k in ("title", "title_english", "title_japanese")
              for x in names_from(sample.get(k))}
    rated: list[dict] = []
    for item in matches:
        alts = [item["title"], *item["aliases"]]
        keys = [v1.title_key(x) for x in alts if x]
        id_match = (sample.get("mal_id") is not None and
                    item.get("mal_id") is not None and
                    str(sample["mal_id"]) == str(item["mal_id"]))
        exact = any(k in wanted for k in keys if k)
        strength = "SAME_MAL_ID" if id_match else "EXACT_TITLE" if exact else "SUGGESTION_ONLY"
        similarity = max((SequenceMatcher(None, x, y).ratio()
                          for x in wanted for y in keys if x and y), default=0)
        rated.append({**item, "evidence": strength, "score": round(similarity, 3),
                      "warning": ("TYPE_DERIVATIVE" if
                                  re.search(r"doujin|artbook|novel", item["format"], re.I)
                                  else None)})
    order = {"SAME_MAL_ID": 2, "EXACT_TITLE": 1, "SUGGESTION_ONLY": 0}
    # When only a fuzzy name matches, prefer an ordinary work to a
    # doujinshi/artbook/novel. Keep every candidate in the report.
    rated.sort(key=lambda c: (
        order[c["evidence"]], c["warning"] is None, c["score"]), reverse=True)
    # Deduplicate cross-query hits but never collapse distinct edition/work IDs.
    unique: list[dict] = []
    seen: set[tuple] = set()
    for item in rated:
        key = ("id", item["id"]) if item["id"] else (
            "title", v1.title_key(item["title"]), item["format"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    if not unique:
        return {"status": "NO_MATCH", "candidates": [], "selected_id": None}
    first = unique[0]
    contenders = [c for c in unique[1:]
                  if order[c["evidence"]] == order[first["evidence"]]
                  and abs(c["score"] - first["score"]) < 0.05]
    status = "AMBIGUOUS" if contenders and order[first["evidence"]] > 0 else first["evidence"]
    reasons = ["EQUALLY_PLAUSIBLE_CANDIDATES"] if status == "AMBIGUOUS" else []
    # Language-qualified editions can be kept as distinct suggestions without
    # declaring the parent manga's identity uncertain. They must never be
    # merged into the French edition/volume inventory.
    qualified = []
    if first["evidence"] == "EXACT_TITLE":
        for candidate in unique[1:]:
            match = re.fullmatch(r"(.+?)\s*\(([^)]{2,80})\)", candidate["title"])
            if not match:
                continue
            descriptor = v1.title_key(match.group(2))
            if (re.fullmatch(
                    r"(?:en|in|version)\s+(?:allemand|anglais|francais|espagnol|italien|"
                    r"portugais|japonais|german|english|french|italian|portuguese|"
                    r"spanish|japanese)", descriptor)):
                continue
            prefix = v1.title_key(match.group(1))
            if prefix and prefix in wanted and candidate.get("id") != first.get("id"):
                qualified.append(candidate)
        if qualified:
            status = "AMBIGUOUS"
            reasons.append("SAME_TITLE_DIFFERENT_QUALIFIED_WORK")
    # If ambiguous, carry the explicitly conflicting candidates for a
    # SIDE-BY-SIDE inspection, not to select a canonical edition or work.
    # Never substitute a fuzzy unrelated suggestion for a real contender.
    conflicts = []
    if status == "AMBIGUOUS":
        conflicts = [first]
        for item in [*contenders, *qualified]:
            if item not in conflicts:
                conflicts.append(item)
    return {
        "status": status,
        "selected_id": first.get("id"),
        "candidates": unique[:MAX_CANDIDATES],
        "candidate_count": len(unique),
        "ambiguous_count": len(conflicts) - 1 if status == "AMBIGUOUS" else 0,
        "disambiguation_reasons": reasons,
        "review_candidates": [{
            "id": item.get("id"), "title": item["title"],
            "format": item.get("format")
        } for item in conflicts[:3]]
    }

def validate_id(source: str, value: Any) -> str | None:
    if source not in SOURCES:
        return None
    if isinstance(value, str) and re.fullmatch(r"[1-9]\d{0,14}", value):
        return value
    return None


def _read_bounded_response(response: Any, max_bytes: int) -> bytes | None:
    """Bound *decompressed* JSON bytes while downloading real HTTP responses.

    Request test doubles expose .content only; real requests.Response supports
    streaming so a huge series does not allocate unbounded response memory.
    """
    if isinstance(response, requests.Response):
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                return None
            if chunk:
                chunks.append(chunk)
        return b"".join(chunks)
    raw = response.content
    return raw if len(raw) <= max_bytes else None


def request_public(source: str, kind: str, session: Any, *,
                   query: str | None = None, identifier: str | None = None) -> dict:
    if source not in SOURCES:
        raise ValueError("Fournisseur inconnu")
    headers = {"User-Agent": v1.USER_AGENT, "Accept": "application/json"}
    if kind == "search":
        if not query or len(query) > 200:
            raise ValueError("Recherche non autorisee")
        if source == "scrinis":
            response = session.get(BASE[source] + "/search",
                                   params={"q": query, "limit": MAX_CANDIDATES},
                                   headers=headers, timeout=20, stream=True)
        else:
            response = session.post(BASE[source] + "/series/search",
                                    json={"search": query, "perpage": MAX_CANDIDATES},
                                    headers=headers, timeout=20, stream=True)
    elif kind == "detail":
        safe_id = validate_id(source, identifier)
        if safe_id is None:
            raise ValueError("Identifiant de fiche absent ou invalide")
        response = session.get(BASE[source] + "/series/" + safe_id,
                               headers=headers, timeout=20, stream=True)
    else:
        raise ValueError("Endpoint non autorise")
    try:
        if response.status_code in (401, 403, 429):
            return {"status": "UNAVAILABLE", "http_status": response.status_code}
        if response.status_code >= 400:
            return {"status": "HTTP_ERROR", "http_status": response.status_code}
        allowed_bytes = (
            MAX_DETAIL_RESPONSE if source == "scrinis" and kind == "detail"
            else MAX_RESPONSE
        )
        raw = _read_bounded_response(response, allowed_bytes)
        if raw is None:
            return {"status": "RESPONSE_TOO_LARGE"}
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            return {"status": "INVALID_JSON"}
        if kind == "search":
            data, diagnostic = parse_hits(payload, source=source)
            return (
                {"status": "OK", "candidates": data, "schema": diagnostic}
                if data is not None
                else {"status": "UNKNOWN_SCHEMA", "schema": diagnostic}
            )
        return {"status": "OK", "data": parse_details(source, payload)}
    finally:
        response.close()


def _labels(raw: Any, *, keys=("name", "genre", "category", "title")) -> list[str]:
    if not isinstance(raw, list):
        return []
    result = []
    for row in raw:
        if isinstance(row, str):
            result.append(row)
        elif isinstance(row, dict):
            for key in keys:
                if isinstance(row.get(key), str):
                    result.append(row[key])
                    break
                if isinstance(row.get(key), dict):
                    result.extend(names_from(row[key]))
                    break
    return list(dict.fromkeys(x[:100] for x in result if x))[:15]


def _scrinis_details(body: dict) -> dict:
    """Adapter for the *verified* Scrinis v1 response, not MangaUpdates JSON.

    Official response: public_n, titles.primary/all, taxonomy.genres/tags,
    publication.publisher, editions, volumes[n/isbn_13/medium/edition/lang].
    Only bounded metadata is retained. No user collection write is possible.
    """
    titles = body.get("titles")
    if not isinstance(titles, dict):
        titles = {}
    primary = names_from(titles.get("primary") or
                         body.get("title") or body.get("name"))
    alt = names_from(titles.get("localized_primary"))
    all_titles = titles.get("all")
    if isinstance(all_titles, list):
        for entry in all_titles[:40]:
            if isinstance(entry, dict):
                alt.extend(names_from(entry.get("title")))
    for key in ("title_localized", "alternative_titles", "aliases"):
        alt.extend(names_from(body.get(key)))
    alt = list(dict.fromkeys(x[:200] for x in alt if x))[:15]
    taxonomy = body.get("taxonomy")
    if not isinstance(taxonomy, dict):
        taxonomy = {}
    genres = _labels(taxonomy.get("genres") or body.get("genres"),
                     keys=("label", "name", "genre", "title"))
    themes = _labels(taxonomy.get("tags") or body.get("themes") or body.get("categories"),
                     keys=("label", "name", "theme", "title"))
    demographies = _labels(taxonomy.get("demographics"),
                           keys=("label", "name", "demographic"))
    publication = body.get("publication")
    if not isinstance(publication, dict):
        publication = {}
    publisher = publication.get("publisher")
    publishers = [publisher[:120]] if isinstance(publisher, str) and publisher else []
    if not publishers:
        publishers = _labels(body.get("publishers"), keys=("publisher_name", "name"))
    credits = body.get("credits")
    authors = []
    if isinstance(credits, list):
        authors = list(dict.fromkeys(
            str(c["name"])[:120] for c in credits[:40]
            if isinstance(c, dict) and c.get("role") in ("artist", "author", "writer")
            and isinstance(c.get("name"), str)
        ))[:12]
    volumes = body.get("volumes") or body.get("tomes") or []
    if isinstance(volumes, dict):
        volumes = volumes.get("items") or volumes.get("data") or []
    if not isinstance(volumes, list):
        volumes = []
    editions = []
    listed_editions = body.get("editions")
    if isinstance(listed_editions, list):
        for edition in listed_editions[:25]:
            if not isinstance(edition, dict):
                continue
            editions.append({
                "edition": str(edition.get("edition") or "")[:80],
                "medium": str(edition.get("medium") or "")[:20],
                "lang": str(edition.get("lang") or "")[:20],
                "volume_count": edition.get("volume_count") if isinstance(
                    edition.get("volume_count"), int) else None
            })
    refs = []
    for volume in volumes[:250]:
        if not isinstance(volume, dict):
            continue
        code = volume.get("isbn_13") or volume.get("isbn13") or volume.get("isbn")
        normalized = isbn13(str(code)) if isinstance(code, (str, int)) else None
        if not normalized:
            continue
        num = volume.get("n")
        if num is None:
            num = volume.get("number") or volume.get("volume")
        if isinstance(num, float) and num.is_integer():
            num = int(num)
        refs.append({
            "isbn13": normalized,
            "volume_label": str(num if num is not None else "")[:40],
            "edition_label": str(volume.get("edition") or "")[:80],
            "medium": str(volume.get("medium") or "")[:20],
            "lang": str(volume.get("lang") or "")[:20],
            "released_on": str(volume.get("released_on") or "")[:30],
        })
    # The report limit favours physical French reference data, but never
    # claims these ISBNs are owned by the user.
    refs.sort(key=lambda r: (r["lang"].lower() == "fr" and
                             r["medium"].lower() == "print",
                             r["lang"].lower() == "fr",
                             r["medium"].lower() == "print"), reverse=True)
    top = body.get("isbn_13") or body.get("isbn13") or body.get("isbn")
    normalized_top = isbn13(str(top)) if isinstance(top, (str, int)) else None
    if normalized_top and not any(x["isbn13"] == normalized_top for x in refs):
        refs.append({"isbn13": normalized_top, "volume_label": "",
                     "edition_label": "", "medium": "", "lang": "",
                     "released_on": ""})
    public_n = body.get("public_n")
    series_id = (str(public_n) if isinstance(public_n, int)
                 and not isinstance(public_n, bool) and 0 < public_n < 10**14
                 else pick_id(body))
    return {
        "status": "OK", "id": series_id,
        "title": primary[0][:200] if primary else None, "aliases": alt,
        "work_type": str(body.get("type") or body.get("format") or "")[:60],
        "genres": genres, "themes": themes, "demographics": demographies,
        "publishers": publishers[:12], "authors": authors,
        "editions": editions,
        "book_references": refs[:250], "volume_items_seen": len(volumes),
        "volume_records_scanned": min(len(volumes), 250),
        "volume_scan_truncated": len(volumes) > 250,
        "book_references_valid_in_scan": len(refs),
        "book_references_truncated": len(refs) > 250 or len(volumes) > 250,
        "has_summary": bool(body.get("summary") or body.get("summaries")
                            or body.get("description") or body.get("synopsis")),
    }


def parse_details(source: str, payload: Any) -> dict:
    """Save structured bibliographic evidence only, never covers or long text."""
    if not isinstance(payload, dict):
        return {"status": "UNKNOWN_DETAIL_SCHEMA"}
    body = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if isinstance(body.get("series"), dict):
        body = body["series"]
    if isinstance(body.get("record"), dict):
        body = body["record"]
    if source == "scrinis":
        return _scrinis_details(body)
    title = names_from(body.get("title") or body.get("name"))
    alts = names_from(body.get("associated")) + names_from(body.get("aliases"))
    alts += names_from(body.get("alternative_titles"))
    for key in ("original_title", "title_en", "title_fr", "title_japanese"):
        alts += names_from(body.get(key))
    tags = _labels(body.get("genres"), keys=("genre", "name", "title"))
    themes = _labels(body.get("categories"), keys=("category", "name", "title"))
    themes += _labels(body.get("themes"), keys=("theme", "name", "title"))
    publication = _labels(body.get("publishers"), keys=("publisher_name", "name"))
    authors = _labels(body.get("authors") or body.get("author"),
                      keys=("name", "author_name", "author", "title"))
    # Scrinis describes volumes/tomes. Never equate their ISBN with ownership.
    volumes = body.get("volumes") or body.get("tomes") or []
    if isinstance(volumes, dict):
        volumes = volumes.get("items") or volumes.get("data") or []
    if not isinstance(volumes, list):
        volumes = []
    book_refs = []
    for volume in volumes[:20]:
        if not isinstance(volume, dict):
            continue
        code = volume.get("isbn13") or volume.get("isbn")
        if isinstance(code, str) and (normalized := isbn13(code)):
            book_refs.append({"isbn13": normalized,
                              "volume_label": str(volume.get("number") or volume.get("volume") or "")[:40],
                              "edition_label": str(volume.get("edition") or "")[:80]})
    # A title-level ISBN is catalog evidence, never verified volume ownership.
    top_isbn = body.get("isbn13") or body.get("isbn")
    if isinstance(top_isbn, str) and (normalized := isbn13(top_isbn)):
        book_refs.insert(0, {"isbn13": normalized, "volume_label": "", "edition_label": ""})
    return {
        "status": "OK", "id": pick_id(body, payload),
        "title": title[0][:200] if title else None, "aliases": alts[:15],
        "work_type": str(body.get("type") or body.get("format") or "")[:60],
        "genres": tags, "themes": list(dict.fromkeys(themes))[:15],
        "publishers": publication[:12], "authors": authors[:12],
        "book_references": book_refs[:20],
        "volume_items_seen": len(volumes),
        "has_summary": bool(body.get("description") or body.get("synopsis") or body.get("summary")),
    }


class RateLimitedClient:
    """One shared interval for searches+details per provider, with local 24h cache."""
    def __init__(self, *, session=None, cache_dir=CACHE_DIR, sleep=time.sleep,
                 clock=time.monotonic):
        self.session = session or requests.Session()
        self.cache_dir = cache_dir
        self.sleep = sleep
        self.clock = clock
        self.last: dict[str, float] = {}
        self.disabled: set[str] = set()
        self.counts = Counter()

    def call(self, provider: str, kind: str, *, query=None, identifier=None) -> dict:
        if provider in self.disabled:
            return {"status": "SKIPPED_PROVIDER_UNAVAILABLE"}
        # Scrinis search responses were cached in V2 *after parsing*, with
        # hub_id discarded. Bump Scrinis only so the corrected parser sees
        # fresh supplier JSON; reuse MangaUpdates caches unchanged.
        cache_key = [provider, kind, query, identifier]
        if provider == "scrinis":
            cache_key.append("scrinis_full_volume_references_v4")
        key = hashlib.sha256(json.dumps(cache_key,
                                        ensure_ascii=False).encode("utf-8")).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.is_file():
            try:
                if datetime.now(timezone.utc) - datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc) < timedelta(hours=24):
                    return json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError, UnicodeError):
                pass
        if provider in self.last:
            self.sleep(max(0, PAUSE[provider] - (self.clock() - self.last[provider])))
        self.last[provider] = self.clock()
        self.counts[provider] += 1
        try:
            result = request_public(provider, kind, self.session,
                                    query=query, identifier=identifier)
        except (requests.RequestException, OSError) as exc:
            result = {"status": "NETWORK_ERROR", "error_type": type(exc).__name__}
        if result["status"] == "UNAVAILABLE":
            self.disabled.add(provider)
        if result["status"] == "OK":
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass  # Failure to cache never changes an API result.
        return result


def alternative_query(sample: dict) -> str | None:
    explicit = EXPLICIT_ALIASES.get(sample["title"])
    if explicit:
        return explicit
    primary = v1.title_key(sample["title"])
    for field in ("title_english", "title_japanese"):
        name = str(sample.get(field) or "").strip()
        if name and v1.title_key(name) != primary:
            return name[:200]
    return None


def evaluate(sample: list[dict], *, client=None, detail_budget=DETAIL_BUDGET,
             alternate_budget=ALT_BUDGET, providers=SOURCES) -> dict:
    client = client or RateLimitedClient()
    entries = [{"title": row["title"], "origin": row["origin"],
                "market_target": row.get("market_target", "INTERNATIONAL"),
                "market_target_basis": row.get("market_target_basis"),
                "sources": {}} for row in sample]
    # The per-provider detail budget may be exhausted early. Explicitly
    # declared physical editions are inspected FIRST, then unmatched library
    # entries, recognised owned works, and finally international controls.
    # Stable report order is unchanged because we write via original indexes.
    def detail_priority(index: int) -> tuple[int, int, int]:
        row = sample[index]
        origin_rank = {"pending": 0, "owned": 1, "catalog": 2}.get(row["origin"], 3)
        return (0 if row.get("edition_targets") else 1, origin_rank, index)
    visit_indices = sorted(range(len(sample)), key=detail_priority)
    metrics = {}
    for provider in providers:
        remaining_details = detail_budget
        remaining_alt = alternate_budget
        for index in visit_indices:
            row, record = sample[index], entries[index]
            result = client.call(provider, "search", query=row["title"])
            if result["status"] != "OK":
                failure = {"status": result["status"],
                    "error_type": result.get("error_type"),
                    "http_status": result.get("http_status"),
                    "schema": result.get("schema")}
                failure["matching_review"] = fr_policy.review_entry(row, failure)
                record["sources"][provider] = failure
                continue
            judged = rank(row, result["candidates"])
            judged["search_schema"] = result["schema"]
            judged["search_queries"] = [row["title"]]
            # Bounded second search only for explicit/known alternative titles.
            alias = alternative_query(row)
            if (remaining_alt and alias and judged["status"] not in
                    ("EXACT_TITLE", "SAME_MAL_ID", "AMBIGUOUS")):
                remaining_alt -= 1
                secondary = client.call(provider, "search", query=alias)
                judged["alternate_search_status"] = secondary["status"]
                if secondary["status"] == "OK":
                    judged = rank(row, result["candidates"] + secondary["candidates"])
                    judged["search_schema"] = result["schema"]
                    judged["alternate_schema"] = secondary["schema"]
                    judged["alternate_search_status"] = "OK"
                    judged["search_queries"] = [row["title"], alias]
            judged["detail_status"] = "NOT_REQUESTED"
            judged["detail_priority_reason"] = (
                "DECLARED_PHYSICAL_EDITION_FIRST" if row.get("edition_targets")
                else "LIBRARY_PENDING" if row["origin"] == "pending"
                else "LIBRARY_OWNED" if row["origin"] == "owned"
                else "INTERNATIONAL_CONTROL"
            )
            if judged["status"] == "AMBIGUOUS":
                # The diagnostic may READ the two conflicting series, but
                # never assigns the selected details to a canonical work.
                # Require enough of the user's per-provider budget to compare
                # every recorded contender (up to three), not half a pair.
                candidates_to_review = [
                    obj for obj in judged.get("review_candidates", [])
                    if validate_id(provider, obj.get("id"))
                ]
                if (len(candidates_to_review) >= 2 and
                        remaining_details >= len(candidates_to_review)):
                    judged["competing_details"] = []
                    for obj in candidates_to_review:
                        remaining_details -= 1
                        result = client.call(provider, "detail", identifier=obj["id"])
                        evidence = {
                            "id": obj["id"], "search_title": obj["title"],
                            "search_format": obj.get("format"),
                            "status": result["status"],
                        }
                        if result["status"] == "OK":
                            evidence["details"] = result["data"]
                        else:
                            evidence["http_status"] = result.get("http_status")
                            evidence["error_type"] = result.get("error_type")
                        judged["competing_details"].append(evidence)
                    judged["detail_status"] = "COMPARED_AMBIGUOUS"
                else:
                    judged["detail_status"] = "SKIPPED_AMBIGUOUS"
                    judged["review_not_run_reason"] = (
                        "INSUFFICIENT_DETAIL_BUDGET" if
                        remaining_details < len(candidates_to_review)
                        else "MISSING_CONFIRMED_PROVIDER_IDS")
            elif remaining_details and judged["selected_id"] and judged["status"] in (
                    "EXACT_TITLE", "SAME_MAL_ID"):
                remaining_details -= 1
                detail = client.call(provider, "detail", identifier=judged["selected_id"])
                judged["detail_status"] = detail["status"]
                if detail["status"] == "OK":
                    judged["details"] = detail["data"]
                else:
                    judged["detail_error"] = detail.get("http_status") or detail.get("error_type")
            judged["matching_review"] = fr_policy.review_entry(row, judged)
            record["sources"][provider] = judged
        counts = Counter(row["sources"][provider]["status"] for row in entries)
        comparable = sum(counts.get(x, 0) for x in
                         ("SAME_MAL_ID", "EXACT_TITLE", "AMBIGUOUS",
                          "SUGGESTION_ONLY", "NO_MATCH"))
        ident = counts["SAME_MAL_ID"] + counts["EXACT_TITLE"]
        metrics[provider] = {"statuses": dict(counts),
                             "evaluated": comparable,
                             "has_exact_candidate": sum(
                                 any(c.get("evidence") in ("EXACT_TITLE", "SAME_MAL_ID")
                                     for c in entry["sources"][provider].get("candidates", []))
                                 for entry in entries),
                             "exact_title_or_mal_id": ident,
                             "rate_percent": round(100 * ident / comparable, 1) if comparable else None,
                             "detail_ok": sum(row["sources"][provider].get("detail_status") == "OK"
                                              for row in entries),
                             "with_numeric_id": sum(bool(row["sources"][provider].get("selected_id"))
                                                    for row in entries),
                             "ambiguous_candidate_details_ok": sum(
                                 item.get("status") == "OK"
                                 for entry in entries
                                 for item in entry["sources"][provider].get("competing_details", [])
                             ),
                             "api_requests": client.counts[provider]}
    return {
        "format_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(sample),
        "detail_priority_policy": "DECLARED_EDITION > PENDING > OWNED > CATALOG",
        "declared_edition_entries": sum(bool(s.get("edition_targets")) for s in sample),
        "privacy": "Recherche externe par titre seulement; aucun volume possede, score ou note transmis.",
        "disclaimer": ("Résultats et ISBN éventuels = indices documentaires non confirmés. "
                       "Aucune oeuvre, édition ou possession liée automatiquement."),
        "providers": metrics, "entries": entries,
    }


def save_report(report: dict, directory: Path = REPORT_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    js = directory / f"comparatif_sources_v2_{stamp}.json"
    cs = directory / f"comparatif_sources_v2_{stamp}.csv"
    js.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with cs.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "titre", "segment", "fournisseur", "etat", "candidat_1", "id_1",
            "nombre_candidats", "concurrents_ambigus", "autres_candidats",
            "detail_etat", "titre_detail", "titres_alternatifs",
            "genres", "themes", "isbn_valides_candidats", "references_tomes",
            "editions", "isbn_papier_fr_candidats", "auteurs",
            "fiches_concurrentes_a_verifier", "raison_controle_non_execute",
            "cible_marche", "cible_langue", "cible_support",
            "editions_declarees", "formats_declares",
            "score_oeuvre_indicatif", "etat_oeuvre", "type_oeuvre_indice",
            "score_edition_fr_indicatif", "etat_edition_fr",
            "signaux_edition", "isbn_fr_papier_candidats",
            "priorite_fiches", "isbn_references_incompletes",
            "volumes_parcourus", "isbn_valides_avant_limite",
            "avertissement"])
        writer.writeheader()
        for item in report["entries"]:
            for provider in SOURCES:
                value = item["sources"].get(provider, {})
                candidates = value.get("candidates") or []
                first = candidates[0] if candidates else {}
                detail = value.get("details") or {}
                books = detail.get("book_references") or []
                review = value.get("matching_review") or {}
                work_review = review.get("work") or {}
                edition_review = review.get("edition") or {}
                writer.writerow({
                    "titre": item["title"], "segment": item["origin"],
                    "fournisseur": provider, "etat": value.get("status"),
                    "candidat_1": first.get("title"), "id_1": first.get("id"),
                    "nombre_candidats": value.get("candidate_count", 0),
                    "concurrents_ambigus": value.get("ambiguous_count", 0),
                    "autres_candidats": " | ".join(c["title"] for c in candidates[1:]),
                    "detail_etat": value.get("detail_status"),
                    "titre_detail": detail.get("title"),
                    "titres_alternatifs": " | ".join(detail.get("aliases") or []),
                    "genres": " | ".join(detail.get("genres") or []),
                    "themes": " | ".join(detail.get("themes") or []),
                    "isbn_valides_candidats": " | ".join(b["isbn13"] for b in books),
                    "references_tomes": detail.get("volume_items_seen"),
                    "editions": " | ".join(
                        str(e.get("edition") or "") + " / " +
                        str(e.get("medium") or "") + " / " +
                        str(e.get("lang") or "")
                        for e in detail.get("editions") or []),
                    "isbn_papier_fr_candidats": " | ".join(
                        b["isbn13"] for b in books if b.get("medium") == "print"
                        and b.get("lang") == "fr"),
                    "auteurs": " | ".join(detail.get("authors") or []),
                    "fiches_concurrentes_a_verifier": " | ".join(
                        str(comp.get("search_title") or "")[:90] +
                        " [id=" + str(comp.get("id") or "") +
                        ", " + str(comp.get("search_format") or "") + "] " +
                        ("auteurs=" + ",".join(
                            (comp.get("details") or {}).get("authors") or []
                        )[:160] + " / editeur=" + ",".join(
                            (comp.get("details") or {}).get("publishers") or []
                        )[:160] + " / ISBN FR papier=" + ",".join(
                            b["isbn13"] for b in (comp.get("details") or {}).get("book_references", [])
                            if b.get("lang") == "fr" and b.get("medium") == "print"
                        )[:160] if comp.get("status") == "OK" else
                         "statut=" + str(comp.get("status")))
                        for comp in value.get("competing_details") or []
                    ),
                    "raison_controle_non_execute": value.get("review_not_run_reason") or "",
                    "cible_marche": review.get("market_target", item.get("market_target")),
                    "cible_langue": "fr" if item.get("market_target") == "FR_PRINT" else "",
                    "cible_support": "print" if item.get("market_target") == "FR_PRINT" else "",
                    "editions_declarees": " | ".join(review.get("edition_targets") or []),
                    "formats_declares": " | ".join(review.get("format_hints") or []),
                    "score_oeuvre_indicatif": work_review.get("score"),
                    "etat_oeuvre": work_review.get("status"),
                    "type_oeuvre_indice": work_review.get("type_evidence"),
                    "score_edition_fr_indicatif": edition_review.get("score"),
                    "etat_edition_fr": edition_review.get("status"),
                    "signaux_edition": " | ".join(edition_review.get("signals") or []),
                    "isbn_fr_papier_candidats": " | ".join(
                        edition_review.get("french_print_isbns") or []),
                    "priorite_fiches": value.get("detail_priority_reason") or "",
                    "isbn_references_incompletes": (
                        "OUI" if (detail.get("book_references_truncated") or any(
                            (c.get("details") or {}).get("book_references_truncated")
                            for c in value.get("competing_details") or []))
                        else "NON" if (detail or any(
                            c.get("details") for c in value.get("competing_details") or []))
                        else "NON_EVALUE"),
                    "volumes_parcourus": detail.get("volume_records_scanned"),
                    "isbn_valides_avant_limite": detail.get("book_references_valid_in_scan"),
                    "avertissement": first.get("warning") or "",
                })
    return js, cs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Comparatif mangas V2: fiches et candidats non confirmés")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--detail-limit", type=int, default=12)
    parser.add_argument("--alternate-limit", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50 or not 0 <= args.detail_limit <= 20 or not 0 <= args.alternate_limit <= 10:
        parser.error("limit 1..50, detail-limit 0..20, alternate-limit 0..10")
    with v1.get_postgres_connection() as db:
        sample = v1.select_samples(db, args.limit)
        sample = fr_policy.enrich_sample_targets(db, sample)
    print("Échantillon V2 :", len(sample), dict(Counter(x["origin"] for x in sample)))
    print("Cible bibliographique :", dict(Counter(x["market_target"] for x in sample)))
    print("FR_PRINT = hypothese pour la collection personnelle, non preuve d'edition française.")
    if args.dry_run:
        for i, item in enumerate(sample, 1):
            editions = ", ".join(item.get("edition_targets") or []) or "non précisées"
            print(f'{i:02d}. [{item["origin"]} / {item["market_target"]}] {item["title"]} — éditions : {editions}')
        return 0
    print("Scrinis et MangaUpdates; seuls les TITRES sont transmis (ni éditions, ni quantités).")
    print("Les scores oeuvre/édition sont des indices documentaires : jamais une validation.")
    report = evaluate(sample, detail_budget=args.detail_limit,
                      alternate_budget=args.alternate_limit)
    js, cs = save_report(report)
    print("Comparatif termine :")
    for name, stats in report["providers"].items():
        print(name, json.dumps(stats, ensure_ascii=False))
    print("Rapports locaux :", js, cs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
