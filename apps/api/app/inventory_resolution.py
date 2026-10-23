"""Manual resolution of physical inventory claims to verified *work* IDs.

No title similarity is ever an approval. The owner chooses a specific manga ID,
reviews the source edition/quantities, checks an explicit acknowledgement, and
commits an immutable audit record + a declaration atomically. No ISBN, specific
volumes, ratings, reading progress, or library status are invented or changed.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from apps.api.app.mangadex_discovery import search_verified_mangadex
from apps.api.app.reconciliation_engine import (
    assess_work_candidate, title_key, discovery_terms, summarize_book_evidence,
)
from apps.api.app.matching_quality import (
    search_patterns, rank_candidates, summarize_bnf_quality,
)
from apps.api.app.wikidata_reverse import search_wikidata_mal_titles
from apps.api.app.edition_discovery import search_bnf_by_title, sanitize_title_query
from apps.api.app.inventory_import import (
    UNSPECIFIED, PendingResolveConfirm, PendingResolvePreview,
)

PENDING_SQL = """
SELECT source_key,entry_title,source_reference,work_declared,edition_declared,
       format_hint,main_volumes,duplicate_copies,other_editions_unknown,
       review_status,candidate_ids,content_sha256
FROM user_manga_inventory_pending
WHERE user_id=%(user_id)s AND source_key=%(source_key)s
"""

MANGA_SQL = """
SELECT m.id,m.title,m.title_english,m.title_japanese,m.source_mal_id,
       m.manga_type,m.volumes
FROM manga m WHERE m.id=%(manga_id)s
"""

EXISTING_SQL = """
SELECT edition_key,entry_title,main_volumes,duplicate_copies,
       other_editions_unknown,edition_declared
FROM user_manga_inventory_declaration
WHERE user_id=%(user_id)s AND manga_id=%(manga_id)s
ORDER BY edition_key
"""

REJECTED_SQL = """
SELECT library_status
FROM user_manga_library
WHERE user_id=%(user_id)s AND manga_id=%(manga_id)s
  AND library_status='NOT_INTERESTED'
"""


def edition_key_for_pending(pending: dict[str, Any]) -> str:
    raw = (pending.get("edition_declared") or "").strip()
    return raw.casefold() if raw else UNSPECIFIED


def _review_token(
    pending: dict[str, Any], manga: dict[str, Any], user_id: int,
    existing: list[dict[str, Any]] | None = None,
) -> str:
    # Includes both immutable original claim hash and current catalogue identity.
    # The token is stale if title, source MAL ID, or pending claim changes.
    input_data = {
        "user_id": user_id,
        "source_key": pending["source_key"],
        "content_sha256": pending["content_sha256"],
        "manga_id": manga["id"],
        "title": manga["title"],
        "title_english": manga.get("title_english"),
        "title_japanese": manga.get("title_japanese"),
        "source_mal_id": manga.get("source_mal_id"),
        "edition_key": edition_key_for_pending(pending),
        "existing_editions": existing or [],
    }
    return hashlib.sha256(json.dumps(
        input_data,ensure_ascii=False,sort_keys=True,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def _load_review(cur: Any, user_id: int, source_key: str, manga_id: int,
                 *, lock: bool = False) -> dict[str, Any]:
    query = PENDING_SQL + (" FOR UPDATE" if lock else "")
    cur.execute(query, {"user_id": user_id, "source_key": source_key})
    pending = cur.fetchone()
    if not pending:
        raise HTTPException(status_code=404, detail="Declaration en attente introuvable ou deja resolue.")
    cur.execute(MANGA_SQL, {"manga_id": manga_id})
    manga = cur.fetchone()
    if not manga:
        raise HTTPException(status_code=404, detail="Manga selectionne introuvable dans le catalogue.")
    key = edition_key_for_pending(pending)
    cur.execute(EXISTING_SQL, {"user_id": user_id, "manga_id": manga_id})
    existing = list(cur.fetchall())
    same_edition = any(row["edition_key"] == key for row in existing)
    cur.execute(REJECTED_SQL, {"user_id":user_id, "manga_id":manga_id})
    if cur.fetchone():
        raise HTTPException(status_code=409,
            detail="Cette oeuvre est marquee Sans interet dans la bibliotheque. "
                   "Corriger ce conflit explicitement avant de la relier.")
    return {
        "source": {key: pending.get(key) for key in (
            "source_key","entry_title","source_reference","work_declared",
            "edition_declared","format_hint","main_volumes",
            "duplicate_copies","other_editions_unknown","review_status",
        )},
        "manga": dict(manga),
        "edition_key": key,
        "existing_declarations": existing,
        "same_edition_exists": same_edition,
        "allowed_actions": (
            ["MARK_DUPLICATE"] if same_edition else
            ["CREATE_DECLARATION", "MARK_DUPLICATE"] if existing else
            ["CREATE_DECLARATION"]
        ),
        "confirmation_token": _review_token(pending, manga, user_id, existing),
        "notice": (
            "Compare les déclarations existantes avant de décider de créer "
            "une nouvelle édition ou d'archiver un doublon."
            if existing else
            "Vérifie l'œuvre ET l'édition indiquée par ton inventaire. "
            "Aucun ISBN ni tome exact n'est attribué."
        ),
        "_pending": dict(pending),
    }


def default_search_term(pending: dict[str, Any]) -> str:
    title = (pending.get("work_declared") or pending.get("entry_title") or "").strip()
    # Search hint only. Removing a parenthesized count is NEVER a work match.
    title = re.sub(r"\s*\([^)]{0,80}\)\s*$", "", title).strip()
    return title[:100]


# Bulk review is strictly documentary: source rows and catalogue records
# are read in batches, but no work, edition, ISBN or owned book is confirmed.
MAX_PENDING_TRIAGE = 1000
MAX_TRIAGE_CANDIDATES = 1000

TRIAGE_PENDING_SQL = """
SELECT source_key,entry_title,work_declared,edition_declared,review_status,
       main_volumes,duplicate_copies,other_editions_unknown,candidate_ids
FROM user_manga_inventory_pending
WHERE user_id=%(user_id)s
ORDER BY entry_title,source_key
LIMIT 1001
"""

TRIAGE_CATALOG_SQL = """
WITH work_candidates AS (
    SELECT id FROM manga
     WHERE LOWER(BTRIM(title)) = ANY(%(terms)s)
        OR LOWER(BTRIM(COALESCE(title_english,''))) = ANY(%(terms)s)
        OR LOWER(BTRIM(COALESCE(title_japanese,''))) = ANY(%(terms)s)
    UNION
    SELECT manga_id AS id FROM manga_title_alias
     WHERE LOWER(BTRIM(alias)) = ANY(%(terms)s)
    UNION
    SELECT id FROM manga WHERE id = ANY(%(saved_ids)s)
    UNION
    SELECT manga_id AS id FROM manga_wikidata_fact
     WHERE LOWER(BTRIM(label_fr)) = ANY(%(terms)s)
)
SELECT m.id,m.title,m.title_english,m.title_japanese,m.source_mal_id,
       m.manga_type,m.volumes,
       (SELECT f.label_fr FROM manga_wikidata_fact f
        WHERE f.manga_id=m.id AND f.source_mal_id=m.source_mal_id)
          AS wikidata_label_fr,
       ARRAY(SELECT DISTINCT LOWER(BTRIM(a.alias)) FROM manga_title_alias a
              WHERE a.manga_id=m.id AND LOWER(BTRIM(a.alias)) = ANY(%(terms)s))
          AS exact_aliases,
       COALESCE((SELECT jsonb_agg(jsonb_build_object(
            'alias',a.alias,'source_name',a.source_name,'source_id',a.source_id))
          FROM manga_title_alias a
          WHERE a.manga_id=m.id AND LOWER(BTRIM(a.alias)) = ANY(%(terms)s)),
          '[]'::jsonb) AS exact_alias_evidence
FROM manga m
JOIN work_candidates c ON c.id=m.id
ORDER BY m.popularity ASC NULLS LAST,m.id
LIMIT 1001
"""


# BnF proposals are not a physical ISBN catalogue. Fetch up to 3 records
# per work and the total explicitly. No huge unbounded provider responses.
TRIAGE_BNF_SQL = """
WITH source AS (
  SELECT manga_id,isbn13,title_fr,author_fr,publisher_fr,language_recorded,
         edition_kind_suggested,source_url,
         COUNT(*) OVER (PARTITION BY manga_id) AS work_isbn_count,
         ROW_NUMBER() OVER (PARTITION BY manga_id ORDER BY isbn13) AS rn
  FROM manga_bnf_candidate WHERE manga_id=ANY(%(manga_ids)s)
)
SELECT manga_id,isbn13,title_fr,author_fr,publisher_fr,language_recorded,
       edition_kind_suggested,source_url,work_isbn_count
FROM source WHERE rn<=30
ORDER BY manga_id,isbn13
"""
TRIAGE_REGISTERED_BOOK_SQL = """
WITH source AS (
  SELECT manga_id,isbn13,
         COUNT(*) OVER (PARTITION BY manga_id) AS work_isbn_count,
         ROW_NUMBER() OVER (PARTITION BY manga_id ORDER BY isbn13) AS rn
  FROM manga_fr_edition WHERE manga_id=ANY(%(manga_ids)s)
)
SELECT manga_id,isbn13,work_isbn_count FROM source WHERE rn<=3
ORDER BY manga_id,isbn13
"""

# A query-plan bounded, locally evaluated search for missing titles. This is
# not a fuzzy entity match: a shared word is only a search suggestion.
DISCOVERY_SQL = """
SELECT m.id,m.title,m.title_english,m.title_japanese,m.source_mal_id,
       m.manga_type,m.volumes,
       (SELECT f.label_fr FROM manga_wikidata_fact f WHERE f.manga_id=m.id
        AND f.source_mal_id=m.source_mal_id) AS wikidata_label_fr,
       COALESCE((
         SELECT jsonb_agg(jsonb_build_object('alias',a.alias,
                    'source_name',a.source_name,'source_id',a.source_id))
         FROM manga_title_alias a
         WHERE a.manga_id=m.id AND a.alias ~* ANY(%(patterns)s)
       ),'[]'::jsonb) AS matching_alias_sources
FROM manga m
WHERE m.title ~* ANY(%(patterns)s)
   OR COALESCE(m.title_english,'') ~* ANY(%(patterns)s)
   OR COALESCE(m.title_japanese,'') ~* ANY(%(patterns)s)
   OR EXISTS (
      SELECT 1 FROM manga_title_alias a
      WHERE a.manga_id=m.id AND a.alias ~* ANY(%(patterns)s)
   )
   OR EXISTS (SELECT 1 FROM manga_wikidata_fact f WHERE f.manga_id=m.id
        AND f.label_fr ~* ANY(%(patterns)s)
        AND f.source_mal_id=m.source_mal_id)
ORDER BY m.popularity ASC NULLS LAST,m.id
LIMIT 101
"""


def _triage_term(pending: dict[str, Any]) -> str:
    # Unlike the interactive search, NEVER strip edition suffixes or count
    # markers here: this is evidence for an exact-title suggestion only.
    title = pending.get("work_declared") or pending.get("entry_title") or ""
    return str(title).strip().casefold()


def _saved_candidate_ids(pending: dict[str, Any]) -> set[int]:
    # Saved candidates are hints from an older import, not verified mappings.
    return {x for x in (pending.get("candidate_ids") or [])
            if type(x) is int and x > 0}


def triage_pending_rows(
    pending_rows: list[dict[str, Any]],
    catalog_rows: list[dict[str, Any]],
    declarations: list[dict[str, Any]],
    rejected_ids: set[int],
    *, lookup_limited: bool = False,
    bnf_rows: list[dict[str, Any]] | None = None,
    registered_books: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prepare a read-only, evidence-attributed owner review queue."""
    declared_by_id: dict[int, set[str]] = {}
    for declaration in declarations:
        declared_by_id.setdefault(int(declaration["manga_id"]), set()).add(
            str(declaration["edition_key"])
        )
    groups: dict[str, int] = {}
    items: list[dict[str, Any]] = []
    bnf_rows = bnf_rows or []
    registered_books = registered_books or []
    bnf_by_id: dict[int, list[dict[str, Any]]] = {}
    for book in bnf_rows:
        bnf_by_id.setdefault(int(book["manga_id"]), []).append(book)
    bnf_quality: dict[int, dict[str, Any]] = {}
    for manga in catalog_rows:
        manga_id = int(manga["id"])
        titles = [str(v) for v in (
            manga.get("title"), manga.get("title_english"),
            manga.get("title_japanese"), manga.get("wikidata_label_fr")
        ) if v]
        bnf_quality[manga_id] = summarize_bnf_quality(
            bnf_by_id.get(manga_id, []), titles,
        )
    canonically_identified: dict[str, set[int]] = {}
    for other in catalog_rows:
        for name in (other.get("title"), other.get("title_english"),
                     other.get("title_japanese")):
            if name:
                canonically_identified.setdefault(title_key(name), set()).add(
                    int(other["id"])
                )
    for pending in pending_rows:
        term = _triage_term(pending)
        saved = _saved_candidate_ids(pending)
        exact: list[dict[str, Any]] = []
        prior: list[dict[str, Any]] = []
        for manga in catalog_rows:
            names = (manga.get("title"), manga.get("title_english"),
                     manga.get("title_japanese"))
            primary_exact = bool(term) and any(
                isinstance(name, str) and name.strip().casefold() == term
                for name in names
            )
            alias_exact = bool(term) and (
                term in (manga.get("exact_aliases") or []) or
                term == str(manga.get("wikidata_label_fr") or "").strip().casefold()
            )
            manga_id = int(manga["id"])
            if not primary_exact and not alias_exact and manga_id not in saved:
                continue
            keys = declared_by_id.get(manga_id, set())
            assessment = assess_work_candidate(
                pending, manga,
                canonically_matched_elsewhere=bool(
                    canonically_identified.get(title_key(term), set()) - {manga_id}
                ),
            )
            record = {
                "manga_id": manga_id,
                "title": manga["title"],
                "source_mal_id": manga.get("source_mal_id"),
                "manga_type": manga.get("manga_type"),
                "volume_count_catalog": manga.get("volumes"),
                "suggestion_basis": ("EXACT_CATALOG_TITLE" if primary_exact else
                                     "EXACT_ALIAS" if alias_exact else
                                     "SAVED_IMPORT_SUGGESTION"),
                "has_existing_declaration": bool(keys),
                "same_edition_already_declared":
                    edition_key_for_pending(pending) in keys,
                "library_not_interested": manga_id in rejected_ids,
                "work_verified": False,
                "edition_verified": False,
                "isbn_verified": False,
                "work_reconciliation": assessment,
                "bibliography": {
                    **summarize_book_evidence(
                        manga_id, bnf_rows, registered_books,
                    ),
                    "quality_review": bnf_quality.get(manga_id, {}),
                },
            }
            (exact if primary_exact or alias_exact else prior).append(record)
        exact.sort(key=lambda x: (x["suggestion_basis"] != "EXACT_CATALOG_TITLE",
                                  x["title"].casefold(), x["manga_id"]))
        prior.sort(key=lambda x: (x["title"].casefold(), x["manga_id"]))
        conflicting_saved = any(x["manga_id"] not in {m["manga_id"] for m in exact}
                                for x in prior)
        if lookup_limited:
            category = "INCOMPLETE_LOOKUP"
        elif len(exact) > 1:
            category = "AMBIGUOUS_EXACT"
        elif len(exact) == 1 and conflicting_saved:
            category = "CONFLICTING_SUGGESTIONS"
        elif len(exact) == 1:
            category = (
                "SUSPICIOUS_ALIAS_REVIEW"
                if exact[0]["suggestion_basis"] == "EXACT_ALIAS" and
                exact[0]["work_reconciliation"]["assessment"] == "CONFLICT_REVIEW"
                else "ALIAS_SOURCE_REVIEW"
                if exact[0]["suggestion_basis"] == "EXACT_ALIAS" and
                exact[0]["work_reconciliation"]["assessment"] == "EVIDENCE_INCOMPLETE_REVIEW"
                else "SINGLE_EXACT_SUGGESTION"
            )
        elif prior:
            category = "SAVED_SUGGESTIONS_ONLY"
        else:
            category = "SEARCH_REQUIRED"
        groups[category] = groups.get(category, 0) + 1
        proposals = (exact + prior)[:12]
        items.append({
            "source_key": pending["source_key"],
            "entry_title": pending["entry_title"],
            "work_declared": pending.get("work_declared"),
            "edition_declared": pending.get("edition_declared"),
            "review_status": pending["review_status"],
            "main_volumes": pending["main_volumes"],
            "duplicate_copies": pending["duplicate_copies"],
            "other_editions_unknown": pending["other_editions_unknown"],
            "review_category": category,
            "exact_suggestion_count": len(exact),
            "saved_only_suggestion_count": len(prior),
            "candidate_list_limited": len(exact) + len(prior) > 12,
            "candidates": proposals,
            "suggested_next_step": (
                "DISCOVER_ALTERNATE_TITLES_AND_EXTERNAL_IDS"
                if category == "SEARCH_REQUIRED" else
                "REVIEW_SUSPECT_ALIAS_PROVENANCE"
                if category in ("SUSPICIOUS_ALIAS_REVIEW", "ALIAS_SOURCE_REVIEW") else
                "COMPARE_SOURCES_AND_CONFIRM_WORK_EDITION"
            ),
            "automatic_association": False,
            "manual_confirmation_required": True,
        })
    priority = {
        "SINGLE_EXACT_SUGGESTION": 0,
        "CONFLICTING_SUGGESTIONS": 1,
        "SUSPICIOUS_ALIAS_REVIEW": 2,
        "ALIAS_SOURCE_REVIEW": 2,
        "SAVED_SUGGESTIONS_ONLY": 3,
        "AMBIGUOUS_EXACT": 4,
        "SEARCH_REQUIRED": 5,
        "INCOMPLETE_LOOKUP": 6,
    }
    items.sort(key=lambda row: (priority[row["review_category"]],
                                row["entry_title"].casefold(), row["source_key"]))
    return {
        "count": len(items),
        "review_categories": groups,
        "items": items,
        "lookup_limited": lookup_limited,
        "automatic_association": False,
        "confirmed_editions_written": 0,
        "inventory_mutations": 0,
        "notice": "Tri documentaire : meme un titre exact et un ISBN suggere ne prouvent ni oeuvre ni edition possedee. Confirmer chaque ligne manuellement.",
    }


def create_pending_resolution_router(
    connection_factory: Callable[..., Any], user_id: int = 1
) -> APIRouter:
    router = APIRouter(prefix="/inventory",tags=["Inventaire : rapprochement manuel"])

    @router.get("/pending/triage")
    def pending_triage() -> dict[str, Any]:
        """Prioritize unresolved claims without any supplier call or SQL write."""
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(TRIAGE_PENDING_SQL, {"user_id": user_id})
                pending = list(cur.fetchall())
                pending_limited = len(pending) > MAX_PENDING_TRIAGE
                pending = pending[:MAX_PENDING_TRIAGE]
                terms = sorted({_triage_term(row) for row in pending
                                if _triage_term(row)})
                saved_ids = sorted({manga_id for row in pending
                                    for manga_id in _saved_candidate_ids(row)})
                works = []
                declarations = []
                rejected_ids: set[int] = set()
                bnf_rows: list[dict[str, Any]] = []
                registered_books: list[dict[str, Any]] = []
                lookup_limited = pending_limited
                if terms or saved_ids:
                    cur.execute(TRIAGE_CATALOG_SQL,
                                {"terms": terms, "saved_ids": saved_ids})
                    works = list(cur.fetchall())
                    lookup_limited |= len(works) > MAX_TRIAGE_CANDIDATES
                    works = works[:MAX_TRIAGE_CANDIDATES]
                    manga_ids = [int(row["id"]) for row in works]
                    if manga_ids:
                        cur.execute("""
                            SELECT manga_id,edition_key
                            FROM user_manga_inventory_declaration
                            WHERE user_id=%(user_id)s
                              AND manga_id=ANY(%(manga_ids)s)
                        """, {"user_id": user_id, "manga_ids": manga_ids})
                        declarations = list(cur.fetchall())
                        cur.execute("""
                            SELECT manga_id FROM user_manga_library
                            WHERE user_id=%(user_id)s AND library_status='NOT_INTERESTED'
                              AND manga_id=ANY(%(manga_ids)s)
                        """, {"user_id": user_id, "manga_ids": manga_ids})
                        rejected_ids = {int(x["manga_id"]) for x in cur.fetchall()}
                        cur.execute(TRIAGE_BNF_SQL, {"manga_ids": manga_ids})
                        bnf_rows = list(cur.fetchall())
                        cur.execute(TRIAGE_REGISTERED_BOOK_SQL,
                                    {"manga_ids": manga_ids})
                        registered_books = list(cur.fetchall())
        return triage_pending_rows(
            pending, works, declarations, rejected_ids,
            lookup_limited=lookup_limited,
            bnf_rows=bnf_rows, registered_books=registered_books,
        )

    @router.get("/pending/discover")
    def discover_pending(
        source_key: str = Query(..., min_length=1, max_length=120),

        include_bnf: bool = False,
        include_mangadex: bool = False,
        include_wikidata: bool = False,
    ) -> dict[str, Any]:
        """Explicit per-row second-pass lookup for zero-exact-title cases.

        Local catalog search is word-based only, never auto-confirmed.
        Optional live BnF is a BOOK search, never a MAL/work proof.
        """
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(PENDING_SQL, {"user_id": user_id, "source_key": source_key})
                pending = cur.fetchone()
                if not pending:
                    raise HTTPException(status_code=404,
                                        detail="Ligne en attente introuvable.")
                query = default_search_term(pending)
                words = discovery_terms(query)
                items = []
                truncated = False
                ranking = rank_candidates(query, [])
                md = {"status":"NOT_REQUESTED","items":[]}
                if include_mangadex:
                    try:
                        md = {"status":"CROSS_LINK_CANDIDATES",
                              "items":search_verified_mangadex(cur,query)}
                    except HTTPException as exc:
                        if exc.status_code != 503:
                            raise
                        md = {"status":"PROVIDER_UNAVAILABLE","items":[]}
                if words:
                    patterns = search_patterns(words)
                    cur.execute(DISCOVERY_SQL, {"patterns": patterns})
                    rows = [dict(row) for row in cur.fetchall()]
                    truncated = len(rows) > 100
                    ranking = rank_candidates(
                        query, rows[:100], pending.get("main_volumes"),
                        total_limited=truncated,
                    )
                    for manga in ranking["candidates"]:
                        items.append({
                            "manga_id": int(manga["id"]),
                            "title": manga["title"],
                            "source_mal_id": manga.get("source_mal_id"),
                            "manga_type": manga.get("manga_type"),
                            "volume_count_catalog": manga.get("volumes"),
                            "status": "DISCOVERY_TOKEN_ONLY",
                            "ranking": manga["ranking"],
                            "work_identity_confirmed": False,
                        })
        wiki = {"status":"NOT_REQUESTED","items":[]}
        if include_wikidata:
            try:
                wiki = search_wikidata_mal_titles(query)
                wikidata_ids = [item["source_mal_id"] for item in wiki["items"]]
                if wikidata_ids:
                    with connection_factory() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT id,source_mal_id,title,manga_type,volumes
                                FROM manga WHERE source_mal_id=ANY(%(ids)s)
                            """,{"ids":wikidata_ids})
                            locally = {int(row["source_mal_id"]):dict(row)
                                       for row in cur.fetchall()}
                    for item in wiki["items"]:
                        match=locally.get(item["source_mal_id"])
                        item["local_manga_id"]=match["id"] if match else None
                        item["local_title"]=match["title"] if match else None
            except HTTPException as exc:
                if exc.status_code != 503:
                    raise
                wiki={"status":"PROVIDER_UNAVAILABLE","items":[]}
        bnf = {"status": "NOT_REQUESTED", "items": []}
        if include_bnf:
            try:
                sanitized = sanitize_title_query(query[:90])
                result = search_bnf_by_title(sanitized)
                bnf = {
                    "status": "BOOK_NOTICES_UNVERIFIED",
                    "items": result["items"][:20],
                    "scope": "ISBN_AND_PRINT_NOT_WORK_IDENTITY",
                    "quality_review": summarize_bnf_quality(
                        result["items"][:20], [query],
                    ),
                }
            except ValueError:
                bnf = {"status": "INVALID_BNF_QUERY", "items": []}
            except HTTPException as error:
                if error.status_code != 503:
                    raise
                bnf = {"status": "BNF_UNAVAILABLE", "items": []}
        return {
            "source_key": source_key,
            "query": query,
            "search_tokens": words,
            "catalog_candidates": items,
            "catalog_truncated": truncated,
            "catalog_evidence": "WHOLE_WORD_RANKED_NOT_IDENTITY",
            "ranking_status": ranking["status"],
            "ranking_margin": ranking["ranking_margin"],
            "ranking_is_calibrated_probability": False,
            "catalogue_candidates_seen": ranking["candidate_count"],
            "bnf": bnf,
            "mangadex": md,
            "wikidata": wiki,
            "external_lookup_requested": bool(include_bnf or include_mangadex or include_wikidata),
            "mangadex_followup": "/inventory/pending/external-candidates",
            "automatic_association": False,
            "isbn_ownership_verified": False,
            "writes_performed": False,
        }

    @router.get("/pending/candidates")
    def find_candidates(
        source_key: str = Query(..., min_length=1, max_length=120),
        q: str | None = Query(None, max_length=100),
    ) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(PENDING_SQL, {"user_id":user_id,"source_key":source_key})
                pending = cur.fetchone()
                if not pending:
                    raise HTTPException(status_code=404, detail="Declaration en attente introuvable.")
                initial = default_search_term(pending)
                term = q.strip() if isinstance(q,str) else initial
                matches = []
                if len(term) >= 2:
                    # Wildcards are escaped: user-typed % or _ cannot expand a
                    # title search to the full manga catalogue.
                    pattern = "%" + (term.replace("\\","\\\\")
                        .replace("%","\\%").replace("_","\\_")) + "%"
                    exact = term.casefold()
                    cur.execute("""
                        SELECT m.id,m.title,m.title_english,m.title_japanese,
                               m.source_mal_id,m.volumes,m.manga_type,
                               (SELECT f.label_fr FROM manga_wikidata_fact f
                                WHERE f.manga_id=m.id
                                  AND f.source_mal_id=m.source_mal_id)
                                  AS wikidata_label_fr,
                               COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                 'alias',ta.alias,'source_name',ta.source_name,
                                 'source_id',ta.source_id))
                                FROM manga_title_alias ta
                                WHERE ta.manga_id=m.id
                                  AND LOWER(BTRIM(ta.alias))=%(exact)s),
                                '[]'::jsonb) AS exact_alias_evidence,
                               (SELECT ta.alias FROM manga_title_alias ta
                                WHERE ta.manga_id=m.id AND ta.alias ILIKE %(pattern)s
                                ORDER BY (LOWER(ta.alias)=%(exact)s) DESC,
                                         (ta.language_code='fr') DESC,ta.alias
                                LIMIT 1) AS matched_alias,
                               CASE WHEN LOWER(m.title)=%(exact)s
                                 OR LOWER(COALESCE(m.title_english,''))=%(exact)s
                                 OR LOWER(COALESCE(m.title_japanese,''))=%(exact)s
                                    THEN 'EXACT_TITLE'
                                 WHEN EXISTS (SELECT 1 FROM manga_title_alias ta
                                   WHERE ta.manga_id=m.id AND LOWER(ta.alias)=%(exact)s)
                                    THEN 'EXACT_MULTILINGUAL_ALIAS'
                                 ELSE 'SEARCH_SUGGESTION'
                               END AS suggestion_kind
                        FROM manga m
                        WHERE m.title ILIKE %(pattern)s
                           OR m.title_english ILIKE %(pattern)s
                           OR m.title_japanese ILIKE %(pattern)s
                           OR EXISTS (SELECT 1 FROM manga_title_alias ta
                                WHERE ta.manga_id=m.id AND ta.alias ILIKE %(pattern)s)
                        ORDER BY CASE WHEN LOWER(m.title)=%(exact)s
                                OR LOWER(COALESCE(m.title_english,''))=%(exact)s
                                OR LOWER(COALESCE(m.title_japanese,''))=%(exact)s
                                THEN 0
                                WHEN EXISTS (SELECT 1 FROM manga_title_alias ta
                                    WHERE ta.manga_id=m.id
                                      AND LOWER(ta.alias)=%(exact)s)
                                THEN 1 ELSE 2 END,
                                m.popularity ASC NULLS LAST,m.id
                        LIMIT 12
                    """, {"exact":exact,"pattern":pattern})
                    matches = [dict(row) for row in cur.fetchall()]
                    canonical_ids = {
                        int(manga["id"]) for manga in matches
                        if any(title_key(manga.get(col)) == title_key(term)
                               for col in ("title","title_english","title_japanese")
                               if manga.get(col))
                    }
                    for manga in matches:
                        manga["reconciliation"] = assess_work_candidate(
                            pending, manga,
                            canonically_matched_elsewhere=bool(
                                canonical_ids - {int(manga["id"])}
                            ),
                        )
        return {
            "source_key": source_key,
            "entry_title": pending["entry_title"],
            "edition_declared": pending.get("edition_declared"),
            "work_declared": pending.get("work_declared"),
            "query":term,
            "items":matches,
            "automatic_association":False,
            "notice":"Suggestions de recherche, jamais un rapprochement automatique.",
        }

    @router.get("/pending/external-candidates")
    def external_candidates(
        source_key: str = Query(...,min_length=1,max_length=120),
        q: str = Query(...,min_length=2,max_length=100),
    ) -> dict[str,Any]:
        # External lookups are opt-in, bounded and read only. Validate a
        # pending row belongs to this user's own inventory before calling out.
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(PENDING_SQL, {"user_id":user_id,"source_key":source_key})
                row=cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404,detail="Ligne en attente introuvable.")
                matches=search_verified_mangadex(cur,q)
        return {
            "items":matches,"query":q,"source_name":"MANGADEX",
            "source_url":"https://mangadex.org",
            "automatic_association":False,
            "notice":"MangaDex (non commercial, attribution). "
                     "Seuls les identifiants manga MyAnimeList explicitement "
                     "liés sont présentés ; confirme l'œuvre et l'édition.",
        }

    @router.post("/pending/resolve/preview")
    def preview(payload: PendingResolvePreview) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                review = _load_review(cur,user_id,payload.source_key,payload.manga_id)
        review.pop("_pending")
        return review

    @router.post("/pending/resolve")
    def resolve(payload: PendingResolveConfirm) -> dict[str, Any]:
        if not payload.acknowledge_work_and_edition:
            raise HTTPException(status_code=422,
                detail="Confirme explicitement la bonne oeuvre et l'edition.")
        with connection_factory() as conn:
            with conn.cursor() as cur:
                # Serializes against competing importer / confirm actions.
                cur.execute("SELECT pg_advisory_xact_lock(%(key)s)",
                            {"key":1202038})
                review = _load_review(cur,user_id,payload.source_key,
                                    payload.manga_id,lock=True)
                if payload.confirmation_token != review["confirmation_token"]:
                    raise HTTPException(status_code=409,
                        detail="La declaration ou la fiche a change : refais l'aperçu.")
                pending = review["_pending"]
                manga = review["manga"]
                edition_key = review["edition_key"]
                mode = payload.resolution_mode
                if mode not in review["allowed_actions"]:
                    raise HTTPException(
                        status_code=409,
                        detail="Cette édition figure déjà dans la collection. "
                               "Aucun tome ne sera ajouté : utilise l'archivage du doublon."
                    )
                if review["existing_declarations"] and not payload.acknowledge_existing_inventory:
                    raise HTTPException(
                        status_code=422,
                        detail="Confirme explicitement la comparaison avec les tomes "
                               "déjà déclarés dans la mangathèque."
                    )
                if mode == "CREATE_DECLARATION":
                    cur.execute("""
                        INSERT INTO user_manga_inventory_declaration (
                            user_id,manga_id,edition_key,edition_declared,entry_title,
                            source_reference,format_hint,main_volumes,
                            duplicate_copies,other_editions_unknown
                        ) VALUES (
                            %(user_id)s,%(manga_id)s,%(edition_key)s,
                            %(edition_declared)s,%(entry_title)s,
                            %(source_reference)s,%(format_hint)s,%(main_volumes)s,
                            %(duplicate_copies)s,%(other_editions_unknown)s
                        )
                        ON CONFLICT (user_id,manga_id,edition_key) DO NOTHING
                        RETURNING manga_id
                    """, {
                        "user_id": user_id,
                        "manga_id": manga["id"],
                        "edition_key": edition_key,
                        **{name:pending[name] for name in (
                            "edition_declared","entry_title","source_reference",
                            "format_hint","main_volumes","duplicate_copies",
                            "other_editions_unknown"
                        )},
                    })
                    if not cur.fetchone():
                        raise HTTPException(status_code=409,
                            detail="Cette oeuvre et cette edition viennent deja d'etre liees.")
                # Preserve source row and checksum before consuming the pending
                # record; never delete pending before both inserts succeed.
                audited = {key:value for key,value in pending.items()
                           if key != "candidate_ids"}
                cur.execute("""
                    INSERT INTO user_manga_inventory_resolution (
                        user_id,source_key,manga_id,edition_key,
                        original_declaration,original_sha256,resolution_mode
                    ) VALUES (
                        %(user_id)s,%(source_key)s,%(manga_id)s,%(edition_key)s,
                        %(original)s::jsonb,%(original_sha256)s,%(mode)s
                    )
                    ON CONFLICT (user_id,source_key) DO NOTHING
                    RETURNING source_key
                """, {
                    "user_id":user_id,
                    "source_key":payload.source_key,
                    "manga_id":manga["id"],
                    "edition_key":edition_key,
                    "original":json.dumps(audited,ensure_ascii=False,default=str),
                    "original_sha256":pending["content_sha256"],
                    "mode":mode,
                })
                if not cur.fetchone():
                    raise HTTPException(status_code=409,
                        detail="Cette ligne source a deja ete rapprochee.")
                cur.execute("""
                    DELETE FROM user_manga_inventory_pending
                    WHERE user_id=%(user_id)s AND source_key=%(source_key)s
                      AND content_sha256=%(sha)s
                    RETURNING source_key
                """, {
                    "user_id":user_id,"source_key":payload.source_key,
                    "sha":pending["content_sha256"],
                })
                if not cur.fetchone():
                    raise HTTPException(status_code=409,
                        detail="Cette ligne a ete modifiee entre-temps. Aucune ecriture conservee.")
            conn.commit()
        return {
            "status":"confirmed",
            "resolution_mode":mode,
            "new_declaration_created":mode=="CREATE_DECLARATION",
            "source_key":payload.source_key,
            "manga_id":manga["id"],
            "catalog_title":manga["title"],
            "edition_declared":pending["edition_declared"],
            "physical_volumes_declared":pending["main_volumes"],
            "isbn_verified":False,
            "reading_status_modified":False,
            "progress_modified":False,
            "pending_rows_resolved":1,
        }

    return router
