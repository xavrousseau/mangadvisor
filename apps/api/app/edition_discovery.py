"""Discover French bibliographic *book records* via BnF SRU title searches.

No manga-to-book links are inferred. A bibliographic notice is not proof of
current retail availability or complete published-edition coverage.
Search is read-only; linking always goes through the existing ISBN route.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from apps.api.app.collection import (
    BNF_SOURCE, BNF_SRU, edition_kind_from_title,
    isbn13_normalize, safe_bnf_ark,
)

SEARCH_LIMIT = 18
MAX_RECORDS = 30
MAX_RESPONSE_BYTES = 2_000_000
SRW_NS = "http://www.loc.gov/zing/srw/"
DC_NS = "http://purl.org/dc/elements/1.1/"
ISBN13_TOKEN = re.compile(r"(?<![0-9])97[89](?:[\s\-\u2010-\u2015]?[0-9]){10}(?![0-9])")


def clean_title_query(value: str) -> str:
    query = " ".join(value.strip().split())
    if not 3 <= len(query) <= 90:
        raise ValueError("Saisis entre 3 et 90 caractères pour rechercher un titre.")
    # Deliberately reject CQL metacharacters: quotes, asterisks, slashes,
    # backslashes, brackets. Query is used only inside a quoted SRU term.
    if not re.fullmatch(r"[\w\s'’\-.,:!&()]+", query, re.UNICODE):
        raise ValueError("La recherche contient des caractères non autorisés.")
    return query


def extract_valid_isbns(fields: list[str]) -> list[str]:
    result: list[str] = []
    for value in fields:
        for match in ISBN13_TOKEN.finditer(value):
            try:
                isbn = isbn13_normalize(match.group())
            except ValueError:
                continue
            if isbn not in result:
                result.append(isbn)
    return result


def bibliographic_language(values: list[str]) -> str:
    """Dublin Core language when supplied, otherwise explicitly unknown."""
    if not values:
        return "unknown"
    tokens = set(re.findall(r"[\\wÀ-ÿ]+", " ".join(values).casefold()))
    french = bool(tokens & {"fr", "fra", "fre", "français", "french"})
    other = tokens - {"fr", "fra", "fre", "français", "french"}
    if french and not other:
        return "french"
    if french:
        return "mixed"
    return "other"


def parse_title_results(xml_bytes: bytes, checked_at: str,
                        limit: int = SEARCH_LIMIT) -> list[dict[str, Any]]:
    if len(xml_bytes) > MAX_RESPONSE_BYTES or re.search(
        rb"<!\s*(?:DOCTYPE|ENTITY)\b", xml_bytes, re.I
    ):
        raise ValueError("Réponse bibliographique trop grande ou XML non sûr.")
    root = ET.fromstring(xml_bytes)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in root.findall(f".//{{{SRW_NS}}}record"):
        ark = safe_bnf_ark(record.findtext(f"{{{SRW_NS}}}recordIdentifier", default=""))
        if not ark:
            continue
        fields: dict[str, list[str]] = {}
        for elem in record.findall(f".//{{{DC_NS}}}*"):
            if elem.text and elem.text.strip():
                name = elem.tag.rsplit("}", 1)[-1]
                fields.setdefault(name, []).append(elem.text.strip())
        title = next(iter(fields.get("title", [])), "")
        if not title:
            continue
        identifiers = extract_valid_isbns(fields.get("identifier", []))
        creators = fields.get("creator") or fields.get("contributor") or []
        publishers = fields.get("publisher") or []
        dates = fields.get("date") or []
        for isbn in identifiers:
            if isbn in seen:
                continue
            seen.add(isbn)
            items.append({
                "isbn13": isbn,
                "title_fr": title[:350],
                "author_fr": "; ".join(creators[:4])[:350] or None,
                "publisher_fr": "; ".join(publishers[:2])[:200] or None,
                "release_date_text": dates[0][:80] if dates else None,
                "language_status": bibliographic_language(fields.get("language", [])),
                "edition_kind_suggested": edition_kind_from_title(title),
                "source_name": BNF_SOURCE,
                "source_url": "https://catalogue.bnf.fr/" + ark,
                "source_checked_at": checked_at,
                "verified_isbn": True,
            })
            if len(items) >= limit:
                return items
    return items


def lookup_title_records(title: str) -> dict[str, Any]:
    title = clean_title_query(title)
    params = urllib.parse.urlencode({
        "version": "1.2", "operation": "searchRetrieve",
        "query": f'bib.title all "{title}"',
        "recordSchema": "dublincore",
        "maximumRecords": MAX_RECORDS,
    })
    request = urllib.request.Request(
        BNF_SRU + "?" + params,
        headers={
            "User-Agent": "Mangadvisor-local/1.2 (French book title discovery)",
            "Accept": "application/xml",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        checked = datetime.now(timezone.utc).isoformat()
        items = parse_title_results(raw, checked)
    except (urllib.error.URLError, OSError, TimeoutError,
            ET.ParseError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Le catalogue BnF est momentanément indisponible pour cette recherche.",
        ) from exc
    return {
        "query": title, "items": items, "count": len(items),
        "limit": SEARCH_LIMIT, "source_name": BNF_SOURCE,
        "checked_at": checked,
        "is_exhaustive": False,
        "scope": "bnf_title_search_isbn_records_only",
        "note": (
            "Sélection limitée de notices BnF contenant un ISBN-13 valide, "
            "sans garantie de langue française lorsque celle-ci n'est pas renseignée. "
            "Ni inventaire complet des tomes publiés, ni preuve de vente actuelle, "
            "ni rattachement automatique à ce manga."
        ),
    }


def create_edition_discovery_router() -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["Collection française"])

    @router.get("/discover-books")
    def discover_books(query: str = Query(..., min_length=3, max_length=90)) -> dict[str, Any]:
        try:
            normalized = clean_title_query(query)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return lookup_title_records(normalized)

    return router
