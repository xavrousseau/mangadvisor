"""Mangadvisor 3.8: safe inventory declarations from a private CSV (no ISBN guessing).

This inventory is NOT verified French book data: no individual ISBN, exact
volume numbers, read status or favorite can be inferred from counts.
Confirmed work matches are written separately from verified ISBN holdings.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

MAX_ROWS = 250
MAX_BYTES = 110_000
UNSPECIFIED = "__UNSPECIFIED__"

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_manga_inventory_declaration (
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    edition_key TEXT NOT NULL,
    edition_declared TEXT,
    entry_title TEXT NOT NULL,
    source_reference TEXT,
    format_hint TEXT,
    main_volumes INTEGER NOT NULL CHECK (main_volumes BETWEEN 0 AND 9999),
    duplicate_copies INTEGER NOT NULL CHECK (duplicate_copies BETWEEN 0 AND 9999),
    other_editions_unknown INTEGER NOT NULL CHECK (other_editions_unknown BETWEEN 0 AND 9999),
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, manga_id, edition_key),
    CHECK ((edition_key = '__UNSPECIFIED__' AND edition_declared IS NULL)
        OR (edition_key <> '__UNSPECIFIED__' AND edition_declared IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS user_manga_inventory_declaration_work_idx
  ON user_manga_inventory_declaration(user_id, manga_id);

-- Preserve owner declarations without inventing a canonical manga identifier.
CREATE TABLE IF NOT EXISTS user_manga_inventory_pending (
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    source_key TEXT NOT NULL,
    entry_title TEXT NOT NULL,
    source_reference TEXT,
    work_declared TEXT,
    edition_declared TEXT,
    format_hint TEXT,
    main_volumes INTEGER NOT NULL CHECK (main_volumes BETWEEN 0 AND 9999),
    duplicate_copies INTEGER NOT NULL CHECK (duplicate_copies BETWEEN 0 AND 9999),
    other_editions_unknown INTEGER NOT NULL CHECK (other_editions_unknown BETWEEN 0 AND 9999),
    review_status TEXT NOT NULL CHECK (review_status IN ('REVIEW_MISSING','REVIEW_AMBIGUOUS')),
    candidate_ids INTEGER[] NOT NULL DEFAULT '{}',
    content_sha256 TEXT NOT NULL,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, source_key)
);
CREATE INDEX IF NOT EXISTS user_manga_inventory_pending_user_idx
  ON user_manga_inventory_pending(user_id);

-- Audit of owner-confirmed reconciliations, preserving the original source.
-- Linking a work must never imply ISBNs, exact volumes, or reading progress.
CREATE TABLE IF NOT EXISTS user_manga_inventory_resolution (
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    source_key TEXT NOT NULL,
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE RESTRICT,
    edition_key TEXT NOT NULL,
    original_declaration JSONB NOT NULL,
    original_sha256 TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolution_mode TEXT NOT NULL DEFAULT 'CREATE_DECLARATION'
       CHECK (resolution_mode IN ('CREATE_DECLARATION','MARK_DUPLICATE')),
    PRIMARY KEY (user_id, source_key)
);
CREATE INDEX IF NOT EXISTS user_manga_inventory_resolution_work_idx
  ON user_manga_inventory_resolution(user_id, manga_id);
ALTER TABLE user_manga_inventory_resolution
  ADD COLUMN IF NOT EXISTS resolution_mode TEXT NOT NULL
    DEFAULT 'CREATE_DECLARATION';

"""


class InventoryCsv(BaseModel):
    csv_content: str = Field(..., min_length=10, max_length=MAX_BYTES)


class InventoryApply(InventoryCsv):
    confirmation_token: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    accept_partial: bool = False


class InventorySavePending(InventoryCsv):
    confirmation_token: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class PendingResolvePreview(BaseModel):
    source_key: str = Field(..., min_length=1, max_length=120)
    manga_id: int = Field(..., ge=1)


class PendingResolveConfirm(PendingResolvePreview):
    confirmation_token: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    acknowledge_work_and_edition: bool = False
    resolution_mode: str = Field("CREATE_DECLARATION",
        pattern=r"^(CREATE_DECLARATION|MARK_DUPLICATE)$")
    acknowledge_existing_inventory: bool = False


def ensure_inventory_schema(connection_factory: Callable[..., Any]) -> None:
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


def parse_inventory(content: str) -> list[dict[str, Any]]:
    if len(content.encode("utf-8")) > MAX_BYTES or "\x00" in content:
        raise HTTPException(status_code=422, detail="Inventaire trop volumineux ou invalide.")
    first = content.lstrip("\ufeff").splitlines()[0] if content else ""
    if first.count(";") < 3:
        raise HTTPException(status_code=422, detail="CSV attendu avec séparateur point-virgule.")
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=";", strict=True)
    names = reader.fieldnames or []
    required = {
        "serie", "tomes_principaux", "doublons_identiques",
        "autres_editions_a_identifier",
    }
    if len(names) != len(set(names)) or not required.issubset(names):
        raise HTTPException(status_code=422, detail="Colonnes obligatoires manquantes ou dupliquées.")
    has_work = "oeuvre_commune" in names
    has_edition = "edition_declaree" in names
    if has_work != has_edition:
        raise HTTPException(status_code=422, detail="L'œuvre commune et l'édition vont ensemble.")
    items = []
    try:
        for line, raw in enumerate(reader, start=2):
            if len(items) >= MAX_ROWS:
                raise HTTPException(status_code=422, detail="Maximum 250 entrées par fichier.")
            if None in raw:
                raise HTTPException(status_code=422, detail=f"Ligne {line} : colonnes en trop.")
            name = (raw.get("serie") or "").strip()
            if not name or len(name) > 200:
                raise HTTPException(status_code=422, detail=f"Ligne {line} : titre manquant ou trop long.")
            values: dict[str, int] = {}
            for key in ("tomes_principaux", "doublons_identiques", "autres_editions_a_identifier"):
                value = (raw.get(key) or "").strip()
                if not re.fullmatch(r"\d{1,4}", value) or int(value) > 9999:
                    raise HTTPException(status_code=422, detail=f"Ligne {line} : quantité {key} invalide.")
                values[key] = int(value)
            if sum(values.values()) == 0:
                raise HTTPException(status_code=422, detail=f"Ligne {line} : aucune possession déclarée.")
            work = (raw.get("oeuvre_commune") or "").strip() if has_work else ""
            edition = (raw.get("edition_declaree") or "").strip() if has_edition else ""
            if bool(work) != bool(edition) or len(work) > 200 or len(edition) > 100:
                raise HTTPException(status_code=422, detail=f"Ligne {line} : œuvre/édition incohérente.")
            if edition.casefold() == UNSPECIFIED.casefold():
                raise HTTPException(status_code=422, detail=f"Ligne {line} : libellé d'édition réservé.")
            source = (raw.get("ligne_source") or "").strip()[:120]
            hint = (raw.get("format_catalogue_provisoire") or "").strip()[:100]
            items.append({
                "line": line,
                "entry_title": name,
                "search_title": work or name,
                "work_declared": work or None,
                "edition_declared": edition or None,
                "edition_key": edition.casefold() if edition else UNSPECIFIED,
                "format_hint": hint or None,
                "source_reference": source or None,
                "main_volumes": values["tomes_principaux"],
                "duplicate_copies": values["doublons_identiques"],
                "other_editions_unknown": values["autres_editions_a_identifier"],
            })
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail=f"CSV illisible : {exc}") from exc
    if not items:
        raise HTTPException(status_code=422, detail="Aucune entrée à importer.")
    return items


def title_key(value: str | None) -> str:
    # Exact title only. Never strip punctuation, reassign franchise variants
    # or assume French transliterations / implicit physical edition names.
    return (value or "").strip().casefold()


def attach_inventory_matches(
    items: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    library: list[dict[str, Any]],
) -> dict[str, Any]:
    by_title: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for manga in catalog:
        for field in ("title", "title_english", "title_japanese"):
            key = title_key(manga.get(field))
            if key:
                by_title[key][int(manga["id"])] = manga
    by_existing = {
        (int(item["manga_id"]), item["edition_key"]): item for item in existing
    }
    by_library = {int(row["manga_id"]): row["library_status"] for row in library}
    proposed = []
    for row in items:
        variants = by_title.get(title_key(row["search_title"]), {})
        manga = next(iter(variants.values())) if len(variants) == 1 else None
        state = ("REVIEW_MISSING" if not variants else
                 "REVIEW_AMBIGUOUS" if len(variants) > 1 else "READY")
        previous = None
        if manga:
            previous = by_existing.get((int(manga["id"]), row["edition_key"]))
            if previous:
                unchanged = all(
                    previous[key] == row[key]
                    for key in ("entry_title","edition_declared","main_volumes",
                                "duplicate_copies","other_editions_unknown",
                                "source_reference","format_hint")
                )
                state = "UNCHANGED" if unchanged else "REVIEW_EXISTING"
            if by_library.get(int(manga["id"])) == "NOT_INTERESTED":
                state = "REVIEW_LIBRARY_CONFLICT"
        proposed.append({
            **row, "manga_id":int(manga["id"]) if manga else None,
            "catalog_title":manga["title"] if manga else None,
            "match":"EXACT_UNIQUE" if manga else (
                "AMBIGUOUS" if variants else "NONE"),
            "candidate_ids":sorted(variants),
            "status":state,
            "existing_library_status":by_library.get(int(manga["id"])) if manga else None,
        })
    # Avoid silently merging two lines with same target work+physical edition,
    # even if their displayed source titles or declared counts differ.
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for i, row in enumerate(proposed):
        if row["manga_id"] is not None:
            groups[(row["manga_id"], row["edition_key"])].append(i)
    for indices in groups.values():
        if len(indices) > 1:
            for idx in indices:
                proposed[idx]["status"] = "REVIEW_DUPLICATE_EDITION"
    return {
        "items": proposed,
        "counts": dict(Counter(x["status"] for x in proposed)),
        "ready": sum(x["status"] == "READY" for x in proposed),
        "unchanged": sum(x["status"] == "UNCHANGED" for x in proposed),
        "review": sum(x["status"].startswith("REVIEW_") for x in proposed),
        "declared_physical_volumes": sum(
            x["main_volumes"] + x["duplicate_copies"] + x["other_editions_unknown"]
            for x in proposed
        ),
        "message":"Aucun ISBN ni tome précis n'est inféré. Les lignes incertaines sont exclues de l'import.",
    }


def preview_hash(review: dict[str, Any], user_id: int) -> str:
    # Comparison token covers all row content, resolved IDs and existing
    # library status. This is a stale-preview detector, NOT authentication.
    contents = json.dumps(
        {"user_id": user_id, "items": review["items"]},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(contents).hexdigest()



def pending_key(row: dict[str, Any]) -> str:
    """Stable position in the original collection, never a guessed manga ID."""
    return (row.get("source_reference") or "").strip() or f"csv-line:{row['line']}"


def suspicious_title_encoding(value: str) -> bool:
    """Detect common double-decoded UTF-8 sequences without altering titles.

    Prevent saving corrupted source claims under a stable source key:
    later fixes should not have to overwrite a falsely preserved title.
    """
    sequences = ("Ã©", "Ã´", "Ã¯", "Â°", "â" + chr(128), "â€")
    return any(part in value for part in sequences)


def pending_hash(row: dict[str, Any]) -> str:
    """Detect changes to owner claims without the catalogue's mutable guesses."""
    fields = ("entry_title", "source_reference", "work_declared",
              "edition_declared", "format_hint", "main_volumes",
              "duplicate_copies", "other_editions_unknown")
    raw = json.dumps({key: row.get(key) for key in fields},
                     ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def summarize_declarations(items: list[dict[str, Any]]) -> dict[str, int]:
    """Physical counts are owner declarations, NOT verified ISBN or reading data."""
    return {
        "works": len({int(row["manga_id"]) for row in items}),
        "edition_entries": len(items),
        "main_volumes": sum(int(row["main_volumes"]) for row in items),
        "identical_duplicates": sum(int(row["duplicate_copies"]) for row in items),
        "other_editions_unidentified": sum(int(row["other_editions_unknown"]) for row in items),
        "physical_total_declared": sum(
            int(row["main_volumes"]) + int(row["duplicate_copies"])
            + int(row["other_editions_unknown"]) for row in items
        ),
    }


def inventory_router(connection_factory: Callable[..., Any], user_id: int = 1) -> APIRouter:
    router = APIRouter(prefix="/inventory", tags=["Inventaire physique privé"])

    def evaluate(cur: Any, entries: list[dict[str, Any]]) -> dict[str, Any]:
        names = list(dict.fromkeys(row["search_title"] for row in entries))
        cur.execute("""
            SELECT id,title,title_english,title_japanese
              FROM manga
             WHERE LOWER(BTRIM(title)) = ANY(%(titles)s)
                OR LOWER(BTRIM(COALESCE(title_english,''))) = ANY(%(titles)s)
                OR LOWER(BTRIM(COALESCE(title_japanese,''))) = ANY(%(titles)s)
             ORDER BY id
        """, {"titles":[name.lower().strip() for name in names]})
        catalog = cur.fetchall()
        cur.execute("""
            SELECT manga_id,edition_key,edition_declared,entry_title,
                   main_volumes,duplicate_copies,other_editions_unknown,
                   source_reference,format_hint
              FROM user_manga_inventory_declaration
             WHERE user_id=%(user_id)s
        """, {"user_id":user_id})
        existing = cur.fetchall()
        cur.execute("""
            SELECT manga_id,library_status FROM user_manga_library
             WHERE user_id=%(user_id)s
        """, {"user_id":user_id})
        library = cur.fetchall()
        review=attach_inventory_matches(entries,catalog,existing,library)
        review["confirmation_token"]=preview_hash(review,user_id)
        return review

    @router.post("/preview")
    def preview(payload: InventoryCsv) -> dict[str, Any]:
        entries=parse_inventory(payload.csv_content)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                return evaluate(cur,entries)

    @router.post("/pending/save")
    def save_pending(payload: InventorySavePending) -> dict[str, Any]:
        """Explicit owner-confirmed, additive preservation of unresolved CSV rows.

        No manga IDs, ISBNs or read status are created here. Existing
        pending claims with different counts/titles are never overwritten.
        """
        entries = parse_inventory(payload.csv_content)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(%(key)s);", {"key": 1202038})
                review = evaluate(cur, entries)
                if preview_hash(review, user_id) != payload.confirmation_token:
                    raise HTTPException(
                        status_code=409,
                        detail="L'inventaire ou le catalogue a change : refais l'apercu.",
                    )
                pending = [
                    row for row in review["items"]
                    if row["status"] in ("REVIEW_MISSING", "REVIEW_AMBIGUOUS")
                ]
                garbled = [
                    row["line"] for row in pending
                    if suspicious_title_encoding(row["entry_title"])
                ]
                if garbled:
                    raise HTTPException(
                        status_code=422,
                        detail="Certains titres du CSV semblent mal encodes (lignes {}). "
                               "Corrige le fichier en UTF-8 avant de conserver "
                               "ces declarations : aucune ecriture.".format(garbled),
                    )
                keys = [pending_key(row) for row in pending]
                if len(keys) != len(set(keys)):
                    raise HTTPException(
                        status_code=422,
                        detail="References de lignes dupliquees : aucune sauvegarde.",
                    )
                cur.execute("""
                    SELECT source_key,content_sha256 FROM user_manga_inventory_pending
                    WHERE user_id=%(user_id)s
                """, {"user_id": user_id})
                already = {r["source_key"]: r["content_sha256"] for r in cur.fetchall()}
                conflicts = [row["line"] for row in pending
                             if pending_key(row) in already
                             and pending_hash(row) != already[pending_key(row)]]
                if conflicts:
                    raise HTTPException(
                        status_code=409,
                        detail="Une declaration en attente a change aux lignes {}. "
                               "Aucune modification : correction manuelle requise.".format(conflicts),
                    )
                new = [row for row in pending if pending_key(row) not in already]
                for row in new:
                    cur.execute("""
                        INSERT INTO user_manga_inventory_pending (
                            user_id,source_key,entry_title,source_reference,
                            work_declared,edition_declared,format_hint,
                            main_volumes,duplicate_copies,other_editions_unknown,
                            review_status,candidate_ids,content_sha256
                        ) VALUES (
                            %(user_id)s,%(source_key)s,%(entry_title)s,%(source_reference)s,
                            %(work_declared)s,%(edition_declared)s,%(format_hint)s,
                            %(main_volumes)s,%(duplicate_copies)s,%(other_editions_unknown)s,
                            %(review_status)s,%(candidate_ids)s,%(content_sha256)s
                        )
                        ON CONFLICT (user_id,source_key) DO NOTHING
                        RETURNING source_key
                    """, {
                        "user_id": user_id,
                        "source_key": pending_key(row),
                        "entry_title": row["entry_title"],
                        "source_reference": row.get("source_reference"),
                        "work_declared": row.get("work_declared"),
                        "edition_declared": row.get("edition_declared"),
                        "format_hint": row.get("format_hint"),
                        "main_volumes": row["main_volumes"],
                        "duplicate_copies": row["duplicate_copies"],
                        "other_editions_unknown": row["other_editions_unknown"],
                        "review_status": row["status"],
                        "candidate_ids": row["candidate_ids"],
                        "content_sha256": pending_hash(row),
                    })
                    if cur.fetchone() is None:
                        raise HTTPException(
                            status_code=409,
                            detail="Une declaration a ete creee simultanement : recommence.",
                        )
            conn.commit()
        return {
            "status": "ok",
            "saved": len(new),
            "unchanged_pending": len(pending)-len(new),
            "still_to_review": len(pending),
            "pending_physical_volumes": sum(
                row["main_volumes"] + row["duplicate_copies"]
                + row["other_editions_unknown"] for row in pending
            ),
            "preserved_without_guessing": True,
            "linked_mangas": 0,
            "message": "Declarations conservees sans inventer de manga ou d'ISBN.",
        }

    @router.post("/apply")
    def apply(payload: InventoryApply) -> dict[str, Any]:
        entries=parse_inventory(payload.csv_content)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(%(key)s);", {"key":1202038})
                review=evaluate(cur,entries)
                if review["confirmation_token"] != payload.confirmation_token:
                    raise HTTPException(
                        status_code=409,
                        detail="L'inventaire ou la base a changé : refais l'aperçu.",
                    )
                if review["review"] and not payload.accept_partial:
                    raise HTTPException(
                        status_code=409,
                        detail="Des lignes demandent une vérification. Confirme explicitement l'import partiel.",
                    )
                written = 0
                created_works: set[int] = set()
                for row in review["items"]:
                    if row["status"] != "READY":
                        continue
                    cur.execute("""
                        INSERT INTO user_manga_inventory_declaration (
                           user_id,manga_id,edition_key,edition_declared,entry_title,
                           source_reference,format_hint,main_volumes,duplicate_copies,
                           other_editions_unknown
                        ) VALUES (
                           %(user_id)s,%(manga_id)s,%(edition_key)s,%(edition_declared)s,
                           %(entry_title)s,%(source_reference)s,%(format_hint)s,
                           %(main_volumes)s,%(duplicate_copies)s,%(other_editions_unknown)s
                        )
                        ON CONFLICT (user_id,manga_id,edition_key) DO NOTHING
                        RETURNING manga_id
                    """, {"user_id":user_id,**row})
                    if cur.fetchone() is None:
                        raise HTTPException(status_code=409, detail="Édition créée en parallèle : recommence.")
                    written += 1
                    created_works.add(row["manga_id"])
                # Only create missing work-level OWNED entries. NEVER UPDATE
                # an existing library status, rating, owned/read count or notes.
                if created_works:
                    cur.execute("""
                        INSERT INTO user_manga_library
                            (user_id,manga_id,library_status)
                        SELECT %(user_id)s,x.id,'OWNED'
                          FROM UNNEST(%(ids)s::integer[]) AS x(id)
                        ON CONFLICT (user_id,manga_id) DO NOTHING;
                    """, {"user_id":user_id,"ids":sorted(created_works)})
            conn.commit()
        return {
            "status":"ok","created_declarations":written,
            "works_covered":len(created_works),
            "unchanged":review["unchanged"],"manual_review":review["review"],
            "not_imported_rows":sum(x["status"].startswith("REVIEW_") for x in review["items"]),
            "preserved_reading_notes_scores":True,
            "message":"Seules les œuvres sûres sont ajoutées ; jamais de remplacement des notes/lectures ou attribution d'ISBN.",
        }

    @router.get("/pending")
    def pending_declarations() -> dict[str, Any]:
        """Unresolved source entries: not part of the recommendation library."""
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT source_key,entry_title,source_reference,work_declared,
                           edition_declared,format_hint,main_volumes,
                           duplicate_copies,other_editions_unknown,
                           review_status,candidate_ids,saved_at::text AS saved_at
                    FROM user_manga_inventory_pending
                    WHERE user_id=%(user_id)s
                    ORDER BY entry_title,source_key LIMIT 1000
                """, {"user_id": user_id})
                rows = cur.fetchall()
        return {
            "count": len(rows),
            "items": rows,
            "declared_physical_volumes": sum(
                r["main_volumes"] + r["duplicate_copies"]
                + r["other_editions_unknown"] for r in rows
            ),
            "scope": "unmatched_owner_declarations_no_manga_id_no_isbn",
            "limited": len(rows) == 1000,
        }

    @router.get("/declarations")
    def declarations(manga_id: int | None = None) -> dict[str, Any]:
        if manga_id is not None and manga_id < 1:
            raise HTTPException(status_code=422, detail="Identifiant manga invalide.")
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT d.manga_id,m.title AS work_title,
                           (SELECT a.alias FROM manga_title_alias a
                            WHERE a.manga_id=m.id AND a.language='fr'
                            ORDER BY CASE WHEN a.source_name='BNF_AUTHORITY_WORK' THEN 0 ELSE 1 END,
                                     a.alias LIMIT 1) AS work_title_fr,
                           d.entry_title,
                           d.edition_declared,d.format_hint,d.main_volumes,
                           d.duplicate_copies,d.other_editions_unknown,
                           d.source_reference,d.imported_at::text AS imported_at
                    FROM user_manga_inventory_declaration d
                    JOIN manga m ON m.id=d.manga_id
                    WHERE d.user_id=%(user_id)s
                      AND (%(manga_id)s::integer IS NULL OR d.manga_id=%(manga_id)s)
                    ORDER BY m.title,d.edition_key
                    LIMIT 1000;
                """,{"user_id":user_id,"manga_id":manga_id})
                rows=cur.fetchall()
        return {"count":len(rows),"items":rows,
                "summary":summarize_declarations(rows),
                "scope":"owner_declared_unverified_editions_not_isbn_books",
                "limited":len(rows)==1000}

    return router
