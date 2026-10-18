"""ISBN camera workflow: local match first; explicit, non-destructive confirmation.

A scan and a BnF lookup are READ operations. Only /scan/confirm may write,
and it never changes legacy user_manga_library counters or replaces owned/read.
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.collection import (
    edition_kind_user_choice_is_explicit,
    isbn13_normalize,
    lookup_bnf,
)

EditionKind = Literal["UNKNOWN", "CLASSIC", "DELUXE", "PERFECT", "COLLECTOR", "INTEGRAL", "OTHER"]


class ScanConfirmation(BaseModel):
    isbn13: str = Field(..., min_length=13, max_length=18)
    confirmed: Literal[True]
    is_owned: bool = True
    is_read: bool = False
    manga_id: int | None = Field(default=None, gt=0)
    edition_kind: EditionKind | None = None
    volume_number: int | None = Field(default=None, ge=1, le=9999)


def normalize_isbn(raw: str) -> str:
    try:
        value = isbn13_normalize(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not value.startswith(("978", "979")):
        raise HTTPException(status_code=422, detail="Ce code EAN-13 n'est pas un ISBN de livre.")
    return value


def find_edition(cur: Any, isbn: str, user_id: int) -> dict[str, Any] | None:
    cur.execute("""
        SELECT ed.id AS edition_id, ed.manga_id, m.title AS manga_title,
               ed.isbn13, ed.title_fr, ed.publisher_fr,
               ed.edition_kind, ed.volume_number, ed.source_url,
               COALESCE(st.is_owned,FALSE) AS is_owned,
               COALESCE(st.is_read,FALSE) AS is_read
        FROM manga_fr_edition ed
        JOIN manga m ON m.id=ed.manga_id
        LEFT JOIN user_manga_volume st
          ON st.edition_id=ed.id AND st.user_id=%(user_id)s
        WHERE ed.isbn13=%(isbn)s;
    """, {"isbn": isbn, "user_id": user_id})
    return cur.fetchone()


def scan_router(connection_factory: Callable[..., Any], user_id: int = 1) -> APIRouter:
    router = APIRouter(prefix="/collection/scan", tags=["Scan ISBN"])

    @router.get("/status/{raw_isbn}")
    def scan_status(raw_isbn: str) -> dict[str, Any]:
        isbn = normalize_isbn(raw_isbn)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                edition = find_edition(cur, isbn, user_id)
        return {"isbn13": isbn, "registered": bool(edition), "edition": edition}

    @router.post("/confirm")
    def confirm_scan(payload: ScanConfirmation) -> dict[str, Any]:
        isbn = normalize_isbn(payload.isbn13)
        if not payload.is_owned and not payload.is_read:
            raise HTTPException(status_code=422, detail="Choisis au moins un statut : possédé ou lu.")

        # Avoid an external request for ISBNs already registered locally.
        with connection_factory() as conn:
            with conn.cursor() as cur:
                initial = find_edition(cur, isbn, user_id)
        bnf_record = None
        if initial is None:
            if payload.manga_id is None or payload.edition_kind is None or payload.volume_number is None:
                raise HTTPException(
                    status_code=422,
                    detail="Série, édition et numéro de tome sont requis pour un nouvel ISBN.",
                )
            bnf_record = lookup_bnf(isbn)
            if not bnf_record:
                raise HTTPException(status_code=404, detail="Notice BnF introuvable. Aucun tome ajouté.")

        with connection_factory() as conn:
            with conn.cursor() as cur:
                # Serialize competing scans of the same ISBN before checking uniqueness.
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%(isbn)s));", {"isbn": isbn})
                edition = find_edition(cur, isbn, user_id)
                created = edition is None
                if created:
                    if bnf_record is None:
                        raise HTTPException(status_code=409, detail="ISBN modifié entre deux vérifications. Recommence.")
                    cur.execute("SELECT id FROM manga WHERE id=%(id)s FOR SHARE;", {"id": payload.manga_id})
                    if not cur.fetchone():
                        raise HTTPException(status_code=404, detail="Série introuvable.")
                    data = edition_kind_user_choice_is_explicit(bnf_record, payload.edition_kind)
                    data.update({"manga_id": payload.manga_id, "volume_number": payload.volume_number})
                    cur.execute("""
                        INSERT INTO manga_fr_edition (
                          manga_id, isbn13, title_fr, author_fr, publisher_fr,
                          edition_kind, edition_kind_origin, volume_number, release_date_text,
                          source_name, source_url, source_checked_at
                        ) VALUES (
                          %(manga_id)s, %(isbn13)s, %(title_fr)s, %(author_fr)s, %(publisher_fr)s,
                          %(edition_kind)s, %(edition_kind_origin)s, %(volume_number)s,
                          %(release_date_text)s, %(source_name)s, %(source_url)s, %(source_checked_at)s
                        );
                    """, data)
                    edition = find_edition(cur, isbn, user_id)
                elif payload.manga_id is not None:
                    # A stale preview must not silently relabel an existing ISBN.
                    if (int(edition["manga_id"]) != payload.manga_id or
                        payload.edition_kind != edition["edition_kind"] or
                        payload.volume_number != edition["volume_number"]):
                        raise HTTPException(
                            status_code=409,
                            detail="Cet ISBN est déjà lié à une série ou édition différente. Actualise le scan.",
                        )
                cur.execute("""
                    INSERT INTO user_manga_volume (user_id, edition_id, is_owned, is_read)
                    VALUES (%(user_id)s, %(edition_id)s, %(owned)s, %(read)s)
                    ON CONFLICT (user_id, edition_id) DO UPDATE SET
                        is_owned = user_manga_volume.is_owned OR EXCLUDED.is_owned,
                        is_read = user_manga_volume.is_read OR EXCLUDED.is_read,
                        updated_at = NOW();
                """, {
                    "user_id": user_id, "edition_id": edition["edition_id"],
                    "owned": payload.is_owned, "read": payload.is_read,
                })
                updated = find_edition(cur, isbn, user_id)
            conn.commit()
        return {"status": "created" if created else "updated", "edition": updated,
                "preserved": True}

    return router
