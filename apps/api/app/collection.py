"""Mangadvisor 1.2 — French edition catalog, BnF ISBN lookup, owned/read per book.

An edition is a physical French book (one ISBN), not the original manga work.
All schema changes are additive. Legacy library counts remain untouched.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BNF_SRU = "https://catalogue.bnf.fr/api/SRU"
BNF_SOURCE = "Bibliothèque nationale de France — Catalogue général"
EDITION_KINDS = ("CLASSIC", "DELUXE", "PERFECT", "COLLECTOR", "INTEGRAL", "OTHER", "UNKNOWN")

SCHEMA = """
CREATE TABLE IF NOT EXISTS manga_fr_edition (
  id BIGSERIAL PRIMARY KEY,
  manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
  isbn13 VARCHAR(13) NOT NULL UNIQUE CHECK (isbn13 ~ '^[0-9]{13}$'),
  title_fr TEXT NOT NULL,
  author_fr TEXT,
  publisher_fr TEXT,
  edition_kind_origin TEXT NOT NULL CHECK (edition_kind_origin IN ('BNF_TITLE','USER_CONFIRMED')),
  edition_kind TEXT NOT NULL CHECK (edition_kind IN
    ('CLASSIC','DELUXE','PERFECT','COLLECTOR','INTEGRAL','OTHER','UNKNOWN')),
  volume_number INTEGER NOT NULL CHECK (volume_number BETWEEN 1 AND 9999),
  release_date_text TEXT,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_checked_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (manga_id, edition_kind, volume_number, isbn13)
);
CREATE INDEX IF NOT EXISTS manga_fr_edition_manga_idx
ON manga_fr_edition (manga_id, edition_kind, volume_number);
CREATE TABLE IF NOT EXISTS user_manga_volume (
  user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  edition_id BIGINT NOT NULL REFERENCES manga_fr_edition(id) ON DELETE CASCADE,
  is_owned BOOLEAN NOT NULL DEFAULT FALSE,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, edition_id)
);
"""

class EditionCreate(BaseModel):
    isbn13: str = Field(..., min_length=10, max_length=18)
    edition_kind: Literal["CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER","UNKNOWN"]
    volume_number: int = Field(..., ge=1, le=9999)

class VolumeState(BaseModel):
    is_owned: bool
    is_read: bool


def isbn13_normalize(raw: str) -> str:
    digits = re.sub(r"[\s-]", "", raw)
    if not re.fullmatch(r"\d{13}", digits):
        raise ValueError("Un ISBN-13 de 13 chiffres est nécessaire.")
    checksum = (10 - sum((1 if i % 2 == 0 else 3) * int(n)
                         for i, n in enumerate(digits[:12])) % 10) % 10
    if checksum != int(digits[-1]):
        raise ValueError("ISBN-13 invalide : chiffre de contrôle incorrect.")
    return digits


def edition_kind_from_title(title: str) -> str:
    text = title.casefold()
    for pattern, kind in (
        (r"\bdeluxe\b", "DELUXE"),
        (r"\b(perfect|kanzenban)\b", "PERFECT"),
        (r"\bcollector\b", "COLLECTOR"),
        (r"\b(intégrale|integrale)\b", "INTEGRAL"),
    ):
        if re.search(pattern, text):
            return kind
    # Absence of an edition label is NOT proof of a classic edition.
    return "UNKNOWN"


def isbn_in_identifiers(identifiers: list[str], isbn13: str) -> bool:
    """Match a complete ISBN-13 token, never digits concatenated across labels."""
    for label in identifiers:
        # A BnF identifier may contain other identifiers and punctuation.
        # Do not construct a thirteen-digit candidate across their boundary.
        candidates = re.findall(
            r"(?<![0-9])97[89](?:[\\s\\-\u2010-\u2015]?[0-9]){10}(?![0-9])",
            label,
        )
        for candidate in candidates:
            try:
                if isbn13_normalize(candidate) == isbn13:
                    return True
            except ValueError:
                continue
    return False


def safe_bnf_ark(value: str) -> str | None:
    """Allow only actual BnF record ARKs; never create links to arbitrary URLs."""
    raw = (value or "").strip()
    match = re.fullmatch(
        r"(?:https?://catalogue\\.bnf\\.fr/)?(ark:/12148/cb[0-9A-Za-z]+)",
        raw,
    )
    return match.group(1) if match else None


def verified_fr_overview(editions: list[dict[str, Any]]) -> dict[str, Any]:
    """Sourced book-level facts only; no assumed official title for the work."""
    def unique_values(key: str, limit: int = 8) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for entry in editions:
            raw = entry.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            label = raw.strip()
            if label.casefold() not in seen:
                seen.add(label.casefold())
                values.append(label)
            if len(values) >= limit:
                break
        return values

    return {
        "source_scope": "verified_registered_books_only",
        "titles_fr": unique_values("title_fr", 8),
        "publishers_fr": unique_values("publisher_fr", 8),
        "authors_fr": unique_values("author_fr", 8),
        "edition_types": sorted({str(e["edition_kind"]) for e in editions}),
        "reference_count": len(editions),
    }


def parse_bnf_sru(xml_bytes: bytes, isbn: str) -> dict[str, Any] | None:
    """Parse only trustworthy Dublin Core data; reject ISBN-mismatched records."""
    if len(xml_bytes) > 1_500_000:
        raise ValueError("Notice BnF trop volumineuse.")
    # Reject entity declarations from untrusted remote XML before parsing.
    if re.search(rb"<!\\s*(?:DOCTYPE|ENTITY)\\b", xml_bytes, re.I):
        raise ValueError("La réponse XML BnF contient une déclaration interdite.")
    root = ET.fromstring(xml_bytes)
    ns = {"srw": "http://www.loc.gov/zing/srw/",
          "dc": "http://purl.org/dc/elements/1.1/"}
    for record in root.findall(".//srw:record", ns):
        fields: dict[str, list[str]] = {}
        for node in record.findall(".//{http://purl.org/dc/elements/1.1/}*"):
            key = node.tag.rsplit("}", 1)[-1]
            if node.text and node.text.strip():
                fields.setdefault(key, []).append(node.text.strip())
        # Never attach a record just because its title happens to match.
        identifiers = fields.get("identifier", [])
        if not isbn_in_identifiers(identifiers, isbn):
            continue
        title = next(iter(fields.get("title", [])), "").strip()
        if not title:
            continue
        creators = fields.get("creator") or fields.get("contributor") or []
        publishers = fields.get("publisher") or []
        dates = fields.get("date") or []
        # SRU's recordIdentifier is a BnF identifier, never free-form user HTML.
        ark = safe_bnf_ark(
            record.findtext("srw:recordIdentifier", default="", namespaces=ns)
        )
        if not ark:
            # A traceable record is required before claiming an official notice.
            continue
        catalogue_link = "https://catalogue.bnf.fr/" + ark
        return {
            "isbn13": isbn,
            "title_fr": title[:350],
            "author_fr": "; ".join(creators[:4])[:350] or None,
            "publisher_fr": "; ".join(publishers[:2])[:200] or None,
            "release_date_text": dates[0][:80] if dates else None,
            "edition_kind_suggested": edition_kind_from_title(title),
            "source_name": BNF_SOURCE,
            "source_url": catalogue_link,
            "source_checked_at": datetime.now(timezone.utc).isoformat(),
            "verified_isbn": True,
        }
    return None


def lookup_bnf(isbn: str) -> dict[str, Any] | None:
    isbn = isbn13_normalize(isbn)
    query = urllib.parse.urlencode({
        "version": "1.2", "operation": "searchRetrieve",
        "query": f'bib.isbn all "{isbn}"',
        "recordSchema": "dublincore", "maximumRecords": 3,
    })
    request = urllib.request.Request(
        BNF_SRU + "?" + query,
        headers={"User-Agent": "Mangadvisor-local/1.2 (bibliographic ISBN search)",
                 "Accept": "application/xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=9) as response:
            raw = response.read(1_500_001)
        return parse_bnf_sru(raw, isbn)
    except (urllib.error.URLError, OSError, TimeoutError, ET.ParseError, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="Service BnF temporairement indisponible ; réessaie plus tard."
        ) from exc


def edition_kind_user_choice_is_explicit(record: dict[str, Any], kind: str) -> dict[str, Any]:
    """Never claim a guessed edition kind is sourced from the BnF."""
    return {**record, "edition_kind": kind,
            "edition_kind_origin": ("BNF_TITLE" if kind == record["edition_kind_suggested"]
                                    and kind != "UNKNOWN" else "USER_CONFIRMED")}


def ensure_collection_schema(connection_factory: Callable[..., Any]) -> None:
    """Idempotent additive startup migration; NEVER alters legacy library columns."""
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


def create_collection_router(
    connection_factory: Callable[..., Any], user_id: int = 1
) -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["Collection française"])

    @router.get("/isbn/{isbn}")
    def lookup_isbn(isbn: str) -> dict[str, Any]:
        try:
            normalized = isbn13_normalize(isbn)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        record = lookup_bnf(normalized)
        if not record:
            raise HTTPException(
                status_code=404,
                detail="Aucune notice BnF associée à cet ISBN. Aucun rattachement n'a été effectué.",
            )
        return record

    @router.get("/mangas/{manga_id}/editions")
    def get_editions(manga_id: int) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id = %(manga_id)s;",
                            {"manga_id": manga_id})
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Manga inconnu.")
                cur.execute("""
                    SELECT ed.id, ed.manga_id, ed.isbn13, ed.title_fr, ed.author_fr,
                      ed.publisher_fr, ed.edition_kind, ed.edition_kind_origin, ed.volume_number,
                      ed.release_date_text, ed.source_name, ed.source_url,
                      ed.source_checked_at::text AS source_checked_at,
                      COALESCE(st.is_owned, FALSE) AS is_owned,
                      COALESCE(st.is_read, FALSE) AS is_read
                    FROM manga_fr_edition ed
                    LEFT JOIN user_manga_volume st
                      ON st.edition_id=ed.id AND st.user_id=%(user_id)s
                    WHERE ed.manga_id=%(manga_id)s
                    ORDER BY ed.edition_kind, ed.volume_number, ed.id;
                """, {"manga_id": manga_id, "user_id": user_id})
                entries = cur.fetchall()
        return {
            "manga_id": manga_id, "editions": entries,
            "french_overview": verified_fr_overview(entries),
            "count": len(entries),
            "owned_books": sum(bool(e["is_owned"]) for e in entries),
            "read_books": sum(bool(e["is_read"]) for e in entries),
            "missing_known_books": sum(not bool(e["is_owned"]) for e in entries),
            "scope_note": "Comptage des ISBN français renseignés uniquement ; les anciennes quantités sont conservées séparément.",
        }

    @router.post("/mangas/{manga_id}/editions", status_code=201)
    def add_edition(manga_id: int, payload: EditionCreate) -> dict[str, Any]:
        try:
            isbn = isbn13_normalize(payload.isbn13)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Recheck on the server: never trust a preview or a user-written source label.
        record = lookup_bnf(isbn)
        if not record:
            raise HTTPException(status_code=404,
                                detail="ISBN introuvable à la BnF ; aucune édition ajoutée.")
        data = edition_kind_user_choice_is_explicit(record, payload.edition_kind)
        data.update({"manga_id": manga_id, "volume_number": payload.volume_number})
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%(manga_id)s FOR SHARE;",
                            {"manga_id": manga_id})
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Manga inconnu.")
                cur.execute("SELECT id, manga_id FROM manga_fr_edition WHERE isbn13=%(isbn13)s;",
                            {"isbn13": isbn})
                existing = cur.fetchone()
                if existing:
                    raise HTTPException(status_code=409,
                                        detail="Cet ISBN est déjà enregistré dans le catalogue des éditions.")
                cur.execute("""
                    INSERT INTO manga_fr_edition (
                      manga_id, isbn13, title_fr, author_fr, publisher_fr,
                      edition_kind, edition_kind_origin, volume_number, release_date_text,
                      source_name, source_url, source_checked_at
                    ) VALUES (
                      %(manga_id)s, %(isbn13)s, %(title_fr)s, %(author_fr)s,
                      %(publisher_fr)s, %(edition_kind)s, %(edition_kind_origin)s, %(volume_number)s,
                      %(release_date_text)s, %(source_name)s, %(source_url)s,
                      %(source_checked_at)s
                    ) RETURNING id;
                """, data)
                row = cur.fetchone()
            conn.commit()
        return {"id": row["id"], **data}

    @router.put("/volumes/{edition_id}")
    def update_volume(edition_id: int, payload: VolumeState) -> dict[str, Any]:
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga_fr_edition WHERE id=%(edition_id)s FOR SHARE;",
                            {"edition_id": edition_id})
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Édition introuvable.")
                cur.execute("""
                    INSERT INTO user_manga_volume
                      (user_id, edition_id, is_owned, is_read)
                    VALUES (%(user_id)s, %(edition_id)s, %(is_owned)s, %(is_read)s)
                    ON CONFLICT (user_id,edition_id) DO UPDATE SET
                      is_owned = EXCLUDED.is_owned,
                      is_read = EXCLUDED.is_read,
                      updated_at = now()
                    RETURNING edition_id,is_owned,is_read;
                """, {"user_id": user_id, "edition_id": edition_id,
                      "is_owned": payload.is_owned, "is_read": payload.is_read})
                row = cur.fetchone()
            conn.commit()
        return row

    return router
