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


def create_pending_resolution_router(
    connection_factory: Callable[..., Any], user_id: int = 1
) -> APIRouter:
    router = APIRouter(prefix="/inventory",tags=["Inventaire : rapprochement manuel"])

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
                    matches = list(cur.fetchall())
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
