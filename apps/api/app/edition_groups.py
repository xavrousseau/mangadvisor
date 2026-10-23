"""Explicit edition groups for French printed books, without migrating legacy volumes.

'manga' is the work; a group is one user-confirmed printing/edition; the
existing manga_fr_edition row is ONE BnF-verified ISBN book (a numbered tome).
The user_manga_volume foreign keys stay untouched. Grouping has no inventory
semantics and cannot be inferred from title matching, provider scores or ISBNs.
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.collection import EDITION_KINDS, isbn13_normalize


GROUP_SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_fr_edition_group (
  id BIGSERIAL PRIMARY KEY,
  manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
  edition_key VARCHAR(80) NOT NULL
    CHECK (edition_key ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  label VARCHAR(120) NOT NULL CHECK (LENGTH(BTRIM(label)) BETWEEN 2 AND 120),
  edition_kind TEXT NOT NULL CHECK (edition_kind IN
    ('CLASSIC','DELUXE','PERFECT','COLLECTOR','INTEGRAL','OTHER','UNKNOWN')),
  publisher_fr VARCHAR(200),
  confirmation_origin TEXT NOT NULL DEFAULT 'USER_CONFIRMED'
    CHECK (confirmation_origin = 'USER_CONFIRMED'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(manga_id,edition_key),
  UNIQUE(id,manga_id,edition_kind)
);
-- The book identity is already unique by id. This composite key lets
-- PostgreSQL enforce consistent work, edition category and ISBN at link time.
CREATE UNIQUE INDEX IF NOT EXISTS idx_manga_fr_book_identity
 ON manga_fr_edition(id,manga_id,edition_kind,isbn13);
CREATE TABLE IF NOT EXISTS manga_fr_edition_group_book (
  book_id BIGINT PRIMARY KEY,
  group_id BIGINT NOT NULL,
  manga_id INTEGER NOT NULL,
  edition_kind TEXT NOT NULL,
  isbn13 VARCHAR(13) NOT NULL CHECK (isbn13 ~ '^[0-9]{13}$'),
  confirmation_origin TEXT NOT NULL DEFAULT 'USER_CONFIRMED'
    CHECK (confirmation_origin = 'USER_CONFIRMED'),
  linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  FOREIGN KEY (book_id,manga_id,edition_kind,isbn13)
    REFERENCES manga_fr_edition(id,manga_id,edition_kind,isbn13)
    ON DELETE CASCADE,
  FOREIGN KEY (group_id,manga_id,edition_kind)
    REFERENCES manga_fr_edition_group(id,manga_id,edition_kind)
    ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_manga_fr_group_book_group
 ON manga_fr_edition_group_book(group_id);
"""


class EditionGroupCreate(BaseModel):
    edition_key: str = Field(..., min_length=2, max_length=80,
                             pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str = Field(..., min_length=2, max_length=120)
    edition_kind: Literal[
        "CLASSIC", "DELUXE", "PERFECT", "COLLECTOR", "INTEGRAL", "OTHER", "UNKNOWN"
    ]
    publisher_fr: str | None = Field(default=None, max_length=200)
    confirmation: Literal["CONFIRMER_EDITION"]


class GroupBookLink(BaseModel):
    book_id: int = Field(..., ge=1)
    isbn13: str = Field(..., min_length=10, max_length=18)
    confirmation: Literal["CONFIRMER_RATTACHEMENT"]


def ensure_edition_group_schema(connection_factory: Callable[..., Any]) -> None:
    """Add only tables/indexes. No backfill and no changes to owned/read state."""
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(GROUP_SCHEMA)
        conn.commit()


def create_edition_group_router(connection_factory: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["Editions françaises vérifiées"])

    @router.get("/mangas/{manga_id}/edition-groups")
    def list_groups(manga_id: int) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%s", (manga_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Manga inconnu.")
                cur.execute("""
                    SELECT id,manga_id,edition_key,label,edition_kind,publisher_fr,
                           confirmation_origin,created_at::TEXT AS created_at
                      FROM manga_fr_edition_group
                     WHERE manga_id=%s ORDER BY edition_key,id
                """, (manga_id,))
                groups = list(cur.fetchall())
                cur.execute("""
                    SELECT link.group_id,book.id AS book_id,book.isbn13,
                           book.volume_number,book.title_fr,
                           book.source_name,book.source_url,
                           link.confirmation_origin,link.linked_at::TEXT AS linked_at
                      FROM manga_fr_edition_group_book link
                      JOIN manga_fr_edition book ON book.id=link.book_id
                     WHERE link.manga_id=%s
                     ORDER BY link.group_id,book.volume_number,book.isbn13
                """, (manga_id,))
                books = list(cur.fetchall())
                cur.execute("""
                    SELECT COUNT(*) AS count
                      FROM manga_fr_edition book
                      LEFT JOIN manga_fr_edition_group_book link ON link.book_id=book.id
                     WHERE book.manga_id=%s AND link.book_id IS NULL
                """, (manga_id,))
                ungrouped = cur.fetchone()
        by_group = {group["id"]: {**group, "books": [], "scope": "linked_isbns_only"}
                    for group in groups}
        for book in books:
            by_group[book["group_id"]]["books"].append(book)
        return {
            "manga_id": manga_id,
            "groups": list(by_group.values()),
            "group_count": len(groups),
            "ungrouped_registered_books": int(ungrouped["count"]),
            "ownership_verified": False,
            "published_totals_known": False,
        }

    @router.post("/mangas/{manga_id}/edition-groups", status_code=201)
    def create_group(manga_id: int, payload: EditionGroupCreate) -> dict[str, Any]:
        label = payload.label.strip()
        if len(label) < 2:
            raise HTTPException(status_code=422, detail="Libellé d'édition vide.")
        publisher = payload.publisher_fr.strip() if payload.publisher_fr else None
        if publisher == "":
            publisher = None
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%s FOR SHARE", (manga_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Manga inconnu.")
                cur.execute("""
                    INSERT INTO manga_fr_edition_group
                      (manga_id,edition_key,label,edition_kind,publisher_fr)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (manga_id,edition_key) DO NOTHING
                    RETURNING id
                """, (manga_id, payload.edition_key, label, payload.edition_kind, publisher))
                created = cur.fetchone()
                if not created:
                    raise HTTPException(
                        status_code=409,
                        detail="Cette édition est déjà déclarée pour cette œuvre.")
            conn.commit()
        return {
            "id": created["id"], "manga_id": manga_id,
            "edition_key": payload.edition_key, "label": label,
            "edition_kind": payload.edition_kind, "publisher_fr": publisher,
            "confirmation_origin": "USER_CONFIRMED",
            "books_linked": 0, "ownership_mutations": 0,
        }

    @router.post("/mangas/{manga_id}/edition-groups/{group_id}/books", status_code=201)
    def link_book(manga_id: int, group_id: int, payload: GroupBookLink) -> dict[str, Any]:
        try:
            code = isbn13_normalize(payload.isbn13)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id,manga_id,edition_kind FROM manga_fr_edition_group
                     WHERE id=%s FOR SHARE
                """, (group_id,))
                group = cur.fetchone()
                if group is None:
                    raise HTTPException(status_code=404, detail="Édition inconnue.")
                if group["manga_id"] != manga_id:
                    raise HTTPException(status_code=409,
                                        detail="Édition rattachée à une autre œuvre.")
                cur.execute("""
                    SELECT id,manga_id,edition_kind,isbn13,source_name,source_url
                      FROM manga_fr_edition WHERE id=%s FOR SHARE
                """, (payload.book_id,))
                book = cur.fetchone()
                if book is None:
                    raise HTTPException(status_code=404, detail="Livre ISBN inconnu.")
                if (book["manga_id"] != manga_id or
                        book["edition_kind"] != group["edition_kind"] or
                        book["isbn13"] != code):
                    raise HTTPException(
                        status_code=409,
                        detail="Œuvre, famille d'édition ou ISBN incompatible : aucune association.")
                if not book["source_name"] or not book["source_url"]:
                    raise HTTPException(
                        status_code=409, detail="Livre sans provenance vérifiable.")
                cur.execute("""
                    INSERT INTO manga_fr_edition_group_book
                      (book_id,group_id,manga_id,edition_kind,isbn13)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (book_id) DO NOTHING
                    RETURNING book_id
                """, (payload.book_id, group_id, manga_id, group["edition_kind"], code))
                result = cur.fetchone()
                if result is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Ce livre est déjà rattaché à une édition ; aucun déplacement.")
            conn.commit()
        return {
            "book_id": result["book_id"], "manga_id": manga_id,
            "group_id": group_id, "isbn13": code,
            "confirmation_origin": "USER_CONFIRMED",
            "ownership_mutations": 0,
        }

    return router
