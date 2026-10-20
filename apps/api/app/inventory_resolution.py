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

from apps.api.app.inventory_import import (
    UNSPECIFIED, PendingResolveConfirm, PendingResolvePreview,
)
from apps.api.app.title_aliases import title_key


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


def _review_token(pending: dict[str, Any], manga: dict[str, Any],
                  user_id: int, existing: list[dict[str,Any]] | None = None) -> str:
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
    cur.execute(EXISTING_SQL, {
        "user_id": user_id, "manga_id": manga_id, "edition_key": key
    })
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
        "allowed_actions": (["MARK_DUPLICATE"] if same_edition
                            else ["CREATE_DECLARATION","MARK_DUPLICATE"] if existing
                            else ["CREATE_DECLARATION"]),
        "confirmation_token": _review_token(pending, manga, user_id, existing),
        "notice": (
            "Déclaration physique déjà présente pour cette œuvre. Vérifie "
            "si cette ligne concerne les mêmes livres avant de l'enregistrer."
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

    @router.get("/pending/multilingual-suggestions")
    def multilingual_suggestions() -> dict[str, Any]:
        """Read-only, exact alias-based review hints for the full pending list.

        This is never an automatic importer. If multiple different manga IDs
        share the same multilingual name, ALL stay ambiguous. Existing owned
        manga are especially prominent to prevent duplicated physical counts.
        """
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT source_key,entry_title,work_declared
                    FROM user_manga_inventory_pending
                    WHERE user_id=%(user_id)s
                    ORDER BY entry_title,source_key LIMIT 1000
                """,{"user_id":user_id})
                pending=list(cur.fetchall())
                keys=list(dict.fromkeys(
                    title_key(default_search_term(row)) for row in pending
                ))
                keys=[key for key in keys if key]
                aliases=[]
                if keys:
                    cur.execute("""
                        SELECT a.alias_key,a.alias,a.source_name,a.language,
                               m.id,m.title,m.title_english,
                               EXISTS (
                                 SELECT 1 FROM user_manga_inventory_declaration d
                                 WHERE d.user_id=%(user_id)s AND d.manga_id=m.id
                               ) AS already_in_inventory
                        FROM manga_title_alias a
                        JOIN manga m ON m.id=a.manga_id
                        WHERE a.alias_key=ANY(%(keys)s)
                        ORDER BY a.alias_key,
                                 CASE WHEN a.source_name='BNF_AUTHORITY_WORK'
                                      THEN 0 ELSE 1 END,
                                 m.popularity ASC NULLS LAST,m.id
                        LIMIT 4001
                    """,{"keys":keys,"user_id":user_id})
                    aliases=list(cur.fetchall())
        truncated=len(aliases)>4000
        if truncated:
            return {"count":len(pending),"items":[],
                    "automatic_association":False,
                    "status":"TOO_MANY_ALIASES_REVIEW_MANUALLY"}
        by_key: dict[str, dict[int, dict[str,Any]]] = {}
        for item in aliases:
            group=by_key.setdefault(item["alias_key"],{})
            group.setdefault(int(item["id"]),dict(item))
        output=[]
        for row in pending:
            key=title_key(default_search_term(row))
            unique=by_key.get(key,{})
            suggestion=next(iter(unique.values())) if len(unique)==1 else None
            state=("NO_EXACT_ALIAS" if not unique else
                   "AMBIGUOUS" if len(unique)>1 else
                   "ALREADY_IN_COLLECTION" if suggestion["already_in_inventory"]
                   else "MATCH_POSSIBLE")
            output.append({
                "source_key":row["source_key"],
                "state":state,
                "candidate_count":len(unique),
                "manga_id":suggestion["id"] if suggestion else None,
                "catalog_title":suggestion["title"] if suggestion else None,
                "title_english":suggestion["title_english"] if suggestion else None,
                "matched_alias":suggestion["alias"] if suggestion else None,
                "source_name":suggestion["source_name"] if suggestion else None,
                "already_in_inventory":bool(
                    suggestion and suggestion["already_in_inventory"]
                ),
            })
        return {"count":len(output),"items":output,
                "automatic_association":False,"status":"READY",
                "notice":"Pistes vérifiées uniquement par alias de titre ; "
                         "la correspondance œuvre et édition reste à confirmer."}

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
                    alias_key = title_key(term)
                    alias_pattern = "%" + (alias_key or "nomatchaliaskey") + "%"
                    cur.execute("""
                        SELECT m.id,m.title,m.title_english,m.title_japanese,
                               m.source_mal_id,m.volumes,m.manga_type,
                               (SELECT a.alias FROM manga_title_alias a
                                WHERE a.manga_id=m.id AND a.language='fr'
                                ORDER BY CASE
                                  WHEN a.source_name='BNF_AUTHORITY_WORK' THEN 0
                                  ELSE 1 END, a.alias LIMIT 1) AS title_fr,
                               (SELECT a.alias FROM manga_title_alias a
                                WHERE a.manga_id=m.id AND a.alias_key=%(alias_key)s
                                ORDER BY CASE
                                  WHEN a.source_name='BNF_AUTHORITY_WORK' THEN 0
                                  ELSE 1 END,a.alias LIMIT 1) AS matched_alias,
                               (SELECT a.source_name FROM manga_title_alias a
                                WHERE a.manga_id=m.id AND a.alias_key=%(alias_key)s
                                ORDER BY CASE
                                  WHEN a.source_name='BNF_AUTHORITY_WORK' THEN 0
                                  ELSE 1 END,a.alias LIMIT 1) AS alias_source,
                               EXISTS (
                                  SELECT 1 FROM user_manga_inventory_declaration d
                                  WHERE d.manga_id=m.id AND d.user_id=%(user_id)s
                               ) AS already_in_inventory,
                               COALESCE((
                                 SELECT jsonb_agg(jsonb_build_object(
                                   'edition',d.edition_declared,
                                   'entry_title',d.entry_title,
                                   'main_volumes',d.main_volumes,
                                   'duplicate_copies',d.duplicate_copies,
                                   'other_editions_unknown',d.other_editions_unknown
                                 ) ORDER BY d.edition_key)
                                 FROM user_manga_inventory_declaration d
                                 WHERE d.manga_id=m.id AND d.user_id=%(user_id)s
                               ),'[]'::jsonb) AS known_editions,
                               CASE
                                 WHEN LOWER(m.title)=%(exact)s
                                   OR LOWER(COALESCE(m.title_english,''))=%(exact)s
                                   OR LOWER(COALESCE(m.title_japanese,''))=%(exact)s
                                   OR EXISTS (
                                     SELECT 1 FROM manga_title_alias a
                                     WHERE a.manga_id=m.id
                                       AND a.alias_key=%(alias_key)s
                                   )
                                 THEN 'EXACT_ALIAS' ELSE 'SEARCH_SUGGESTION'
                               END AS suggestion_kind
                        FROM manga m
                        WHERE m.title ILIKE %(pattern)s
                           OR m.title_english ILIKE %(pattern)s
                           OR m.title_japanese ILIKE %(pattern)s
                           OR EXISTS (
                              SELECT 1 FROM manga_title_alias a
                              WHERE a.manga_id=m.id
                                AND a.alias_key LIKE %(alias_pattern)s
                           )
                        ORDER BY CASE WHEN LOWER(m.title)=%(exact)s
                                OR LOWER(COALESCE(m.title_english,''))=%(exact)s
                                OR LOWER(COALESCE(m.title_japanese,''))=%(exact)s
                                OR EXISTS (
                                  SELECT 1 FROM manga_title_alias a
                                  WHERE a.manga_id=m.id
                                    AND a.alias_key=%(alias_key)s)
                                THEN 0 ELSE 1 END,
                                m.popularity ASC NULLS LAST,m.id
                        LIMIT 12
                    """, {"exact":exact,"pattern":pattern,
                           "alias_key":alias_key,
                           "alias_pattern":alias_pattern,"user_id":user_id})
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
                existing = review["existing_declarations"]
                if mode not in review["allowed_actions"]:
                    raise HTTPException(status_code=409,
                        detail="Édition déjà déclarée. Pour éviter les doublons, "
                               "compare les quantités puis choisis l'archivage.")
                if existing and not payload.acknowledge_existing_inventory:
                    raise HTTPException(status_code=422,
                        detail="Tu dois confirmer la comparaison avec les "
                               "déclarations physiques déjà présentes.")
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
            "resolution_mode":payload.resolution_mode,
            "new_declaration_created":payload.resolution_mode=="CREATE_DECLARATION",
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
