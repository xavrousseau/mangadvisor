"""Read-only, bibliographically grounded French edition snapshots for recommendations.

Each row represents one *registered ISBN*, not proof of a full French run or
commercial availability. Unknown editorial format remains UNKNOWN.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from apps.api.app.collection import EDITION_KINDS

MAX_BOOKS_PER_FORMAT = 4


def group_registered_editions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Only emit fields present in the registered source rows. No inferred tomes."""
    by_format: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_isbns: set[str] = set()
    for row in rows:
        isbn = str(row.get("isbn13") or "")
        if not isbn or isbn in seen_isbns:
            continue
        seen_isbns.add(isbn)
        kind = str(row.get("edition_kind") or "UNKNOWN")
        if kind not in EDITION_KINDS:
            kind = "UNKNOWN"
        by_format[kind].append({
            "isbn13": isbn,
            "title_fr": row.get("title_fr"),
            "publisher_fr": row.get("publisher_fr"),
            "author_fr": row.get("author_fr"),
            "volume_number": row.get("volume_number"),
            "release_date_text": row.get("release_date_text"),
            "source_name": row.get("source_name"),
            "source_url": row.get("source_url"),
            "edition_kind_origin": row.get("edition_kind_origin"),
        })

    groups = []
    for kind in EDITION_KINDS:
        books = sorted(
            by_format.get(kind, []),
            key=lambda row: (int(row.get("volume_number") or 999999), row["isbn13"]),
        )
        if not books:
            continue
        publishers = sorted({
            book["publisher_fr"].strip()
            for book in books if isinstance(book["publisher_fr"], str)
            and book["publisher_fr"].strip()
        }, key=str.casefold)
        groups.append({
            "edition_kind": kind,
            "registered_isbn_count": len(books),
            "known_volume_numbers": sorted({
                int(book["volume_number"]) for book in books
                if isinstance(book["volume_number"], int) and book["volume_number"] > 0
            }),
            "publishers_fr": publishers,
            "books_shown": books[:MAX_BOOKS_PER_FORMAT],
            "books_remaining": max(0, len(books) - MAX_BOOKS_PER_FORMAT),
            "format_basis": (
                "registered_catalog_label_or_user_confirmation"
                if kind != "UNKNOWN" else "format_not_established"
            ),
        })
    return {
        "scope": "registered_isbns_only",
        "registered_isbn_count": len(seen_isbns),
        "registered_formats": groups,
        "published_total_known": False,
        "availability_checked": False,
        "complete_french_series": None,
    }


def fetch_recommended_editions(
    connection_factory: Callable[..., Any],
    manga_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """One parameterized, bounded query for the selected recommendation IDs."""
    valid_ids = sorted({i for i in manga_ids if isinstance(i, int) and i > 0})[:12]
    if not valid_ids:
        return {}
    sql = """
        SELECT manga_id, isbn13, title_fr, publisher_fr, author_fr,
               edition_kind, edition_kind_origin, volume_number, release_date_text,
               source_name, source_url
        FROM manga_fr_edition
        WHERE manga_id = ANY(%(manga_ids)s)
        ORDER BY manga_id, edition_kind, volume_number, isbn13
    """
    with connection_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"manga_ids": valid_ids})
            rows = cur.fetchall()
    by_manga: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if int(row["manga_id"]) in valid_ids:
            by_manga[int(row["manga_id"])].append(row)
    return {manga_id: group_registered_editions(by_manga.get(manga_id, []))
            for manga_id in valid_ids}
