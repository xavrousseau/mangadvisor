"""Conservative CSV import for verified French editions, plus read-only reconciliation.

We never infer an edition from a title, call an external service in bulk,
or overwrite user's book or legacy-series progress. ISBN exact matches only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.collection import isbn13_normalize

MAX_ROWS = 250
MAX_BYTES = 80_000
TRUE = {"1", "true", "yes", "y", "oui", "o", "vrai", "x"}
FALSE = {"0", "false", "no", "n", "non", "faux", ""}
ISBN_KEYS = {"isbn", "isbn13", "isbn_13", "isbn-13", "ean", "ean13", "code_barres", "barcode"}
OWNED_KEYS = {"owned", "is_owned", "possede", "possédé", "achete", "acheté"}
READ_KEYS = {"read", "is_read", "lu", "lus", "lue"}


class CsvBooksRequest(BaseModel):
    csv_content: str = Field(..., min_length=5, max_length=MAX_BYTES)


class CsvBooksApply(CsvBooksRequest):
    confirmation_token: str = Field(..., min_length=64, max_length=64)


def normal_header(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().casefold().replace("\ufeff", ""))


def parse_bool(value: str, *, line: int, label: str) -> bool:
    cleaned = value.strip().casefold()
    if cleaned in TRUE:
        return True
    if cleaned in FALSE:
        return False
    raise ValueError(f"Ligne {line} : statut « {label} » invalide, utilise oui ou non.")


def normalize_csv(content: str) -> dict[str, Any]:
    """Preview all rows first; never attempt title/edition guessing."""
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise HTTPException(status_code=422, detail="CSV trop volumineux (80 Ko maximum).")
    if "\x00" in content:
        raise HTTPException(status_code=422, detail="CSV invalide : caractère nul.")
    first = content.lstrip("\ufeff").splitlines()[0] if content else ""
    delimiter = ";" if first.count(";") > max(first.count(","), first.count("\t")) else (
        "\t" if first.count("\t") > first.count(",") else ","
    )
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=delimiter, strict=True)
    headers = reader.fieldnames or []
    mapping = {normal_header(header): header for header in headers if header is not None}
    isbn_col = next((mapping[key] for key in ISBN_KEYS if key in mapping), None)
    # Deterministic choice regardless of unordered set iteration.
    isbn_col = next((mapping[key] for key in ("isbn13", "isbn_13", "isbn-13", "isbn", "ean13", "ean", "code_barres", "barcode") if key in mapping), None)
    owned_col = next((mapping[key] for key in ("possede", "possédé", "is_owned", "owned", "achete", "acheté") if key in mapping), None)
    read_col = next((mapping[key] for key in ("lu", "lus", "is_read", "read", "lue") if key in mapping), None)
    if isbn_col is None:
        raise HTTPException(status_code=422, detail="Colonne ISBN obligatoire (isbn13 ou isbn).")
    grouped: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    total = 0
    try:
        for index, row in enumerate(reader, start=2):
            total += 1
            if total > MAX_ROWS:
                raise HTTPException(status_code=422, detail="Maximum 250 lignes par import.")
            if None in row:
                errors.append({"line": index, "message": "Trop de colonnes pour l'en-tête."})
                continue
            try:
                isbn = isbn13_normalize(str(row.get(isbn_col) or ""))
                owned = parse_bool(str(row.get(owned_col) or "") if owned_col else "oui",
                                   line=index, label="possédé")
                read = parse_bool(str(row.get(read_col) or "") if read_col else "non",
                                  line=index, label="lu")
            except ValueError as exc:
                errors.append({"line": index, "message": str(exc)})
                continue
            entry = grouped.setdefault(isbn, {"isbn13": isbn, "is_owned": False,
                                               "is_read": False, "lines": []})
            entry["is_owned"] = entry["is_owned"] or owned
            entry["is_read"] = entry["is_read"] or read
            entry["lines"].append(index)
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail=f"CSV non valide : {exc}") from exc
    return {"items": list(grouped.values()), "errors": errors,
            "total_rows": total, "duplicate_rows": sum(len(i["lines"])-1 for i in grouped.values())}


def attach_matches(rows: list[dict[str, Any]], known: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog = {x["isbn13"]: x for x in known}
    output = []
    for item in rows:
        found = catalog.get(item["isbn13"])
        output.append({
            **item,
            "match": "EXACT_ISBN" if found else "UNKNOWN",
            "edition_id": found["id"] if found else None,
            "manga_id": found["manga_id"] if found else None,
            "title_fr": found["title_fr"] if found else None,
            "edition_kind": found["edition_kind"] if found else None,
            "volume_number": found["volume_number"] if found else None,
            "was_owned": bool(found.get("is_owned")) if found else False,
            "was_read": bool(found.get("is_read")) if found else False,
        })
    return output


def confirmation_token(items: list[dict[str, Any]], errors: list[dict[str, Any]]) -> str:
    stable = json.dumps({"items": items, "errors": errors}, sort_keys=True,
                        separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def make_preview(parsed: dict[str, Any], known: list[dict[str, Any]]) -> dict[str, Any]:
    items = attach_matches(parsed["items"], known)
    known_count = sum(row["match"] == "EXACT_ISBN" for row in items)
    updates = sum(
        row["match"] == "EXACT_ISBN"
        and ((row["is_owned"] and not row["was_owned"]) or (row["is_read"] and not row["was_read"]))
        for row in items
    )
    return {
        "items": items,
        "errors": parsed["errors"],
        "total_rows": parsed["total_rows"],
        "duplicate_rows": parsed["duplicate_rows"],
        "matched": known_count,
        "unknown": len(items) - known_count,
        "to_update": updates,
        "confirmation_token": confirmation_token(items, parsed["errors"]),
        "message": "Seuls les ISBN déjà vérifiés et enregistrés sont importés. Aucun titre ou éditeur n'est deviné.",
    }


def collection_import_router(connection_factory: Callable[..., Any], user_id: int = 1) -> APIRouter:
    router = APIRouter(prefix="/collection", tags=["Collection française"])

    def preview_in_connection(parsed: dict[str, Any], cur: Any) -> dict[str, Any]:
        ids = [x["isbn13"] for x in parsed["items"]]
        known: list[dict[str, Any]] = []
        if ids:
            cur.execute("""
                SELECT ed.id, ed.isbn13, ed.manga_id, ed.title_fr,
                       ed.edition_kind, ed.volume_number,
                       COALESCE(st.is_owned,FALSE) AS is_owned,
                       COALESCE(st.is_read,FALSE) AS is_read
                FROM manga_fr_edition ed
                LEFT JOIN user_manga_volume st
                  ON st.edition_id=ed.id AND st.user_id=%(user_id)s
                WHERE ed.isbn13=ANY(%(isbns)s)
                ORDER BY ed.isbn13
            """, {"isbns": ids, "user_id": user_id})
            known = cur.fetchall()
        return make_preview(parsed, known)

    @router.post("/import/preview")
    def preview_csv_books(payload: CsvBooksRequest) -> dict[str, Any]:
        parsed = normalize_csv(payload.csv_content)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                return preview_in_connection(parsed, cur)

    @router.post("/import/apply")
    def apply_csv_books(payload: CsvBooksApply) -> dict[str, Any]:
        parsed = normalize_csv(payload.csv_content)
        with connection_factory() as conn:
            with conn.cursor() as cur:
                # Row locking protects already existing collection states between
                # checking the preview token and applying non-destructive updates.
                cur.execute("SELECT pg_advisory_xact_lock(%(lock)s);", {"lock": 1202026})
                review = preview_in_connection(parsed, cur)
                if review["confirmation_token"] != payload.confirmation_token:
                    raise HTTPException(
                        status_code=409,
                        detail="La bibliothèque ou le fichier a changé depuis l'aperçu. Recommence la vérification.",
                    )
                affected = 0
                for item in review["items"]:
                    if item["match"] != "EXACT_ISBN" or (not item["is_owned"] and not item["is_read"]):
                        continue
                    cur.execute("""
                        INSERT INTO user_manga_volume
                            (user_id, edition_id, is_owned, is_read)
                        VALUES (%(user_id)s,%(edition_id)s,%(is_owned)s,%(is_read)s)
                        ON CONFLICT (user_id,edition_id) DO UPDATE SET
                          is_owned = user_manga_volume.is_owned OR EXCLUDED.is_owned,
                          is_read = user_manga_volume.is_read OR EXCLUDED.is_read,
                          updated_at = NOW();
                    """, {"user_id": user_id, "edition_id": item["edition_id"],
                          "is_owned": item["is_owned"], "is_read": item["is_read"]})
                    affected += 1
            conn.commit()
        return {"status": "ok", "matched": review["matched"], "unknown": review["unknown"],
                "processed": affected,
                "preserved": True,
                "message": "Import sans suppression : seuls les statuts oui sont ajoutés ; les données existantes sont conservées."}

    @router.get("/reconciliation")
    def legacy_reconciliation() -> dict[str, Any]:
        # No writes: counts from legacy series + ISBN-level detailed state
        # are deliberately shown side by side, never added together.
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.id AS manga_id, m.title, l.owned_volumes AS legacy_owned,
                           l.read_volumes AS legacy_read,
                           COUNT(ed.id)::int AS known_books,
                           COUNT(ed.id) FILTER (WHERE st.is_owned)::int AS owned_books,
                           COUNT(ed.id) FILTER (WHERE st.is_read)::int AS read_books
                    FROM user_manga_library l
                    JOIN manga m ON m.id=l.manga_id
                    LEFT JOIN manga_fr_edition ed ON ed.manga_id=m.id
                    LEFT JOIN user_manga_volume st
                      ON st.edition_id=ed.id AND st.user_id=l.user_id
                    WHERE l.user_id=%(user_id)s
                    GROUP BY m.id,m.title,l.owned_volumes,l.read_volumes
                    ORDER BY m.title LIMIT 1000;
                """, {"user_id": user_id})
                items = cur.fetchall()
        return {
            "count": len(items), "items": items,
            "legacy_totals": {
                "owned": sum(int(x["legacy_owned"] or 0) for x in items),
                "read": sum(int(x["legacy_read"] or 0) for x in items),
            },
            "isbn_totals": {
                "known": sum(int(x["known_books"]) for x in items),
                "owned": sum(int(x["owned_books"]) for x in items),
                "read": sum(int(x["read_books"]) for x in items),
            },
            "note": "Les anciens compteurs sont des nombres globaux de séries. Les nouveaux compteurs ne couvrent que les ISBN référencés : ils ne sont ni additionnés ni synchronisés automatiquement.",
        }

    return router
