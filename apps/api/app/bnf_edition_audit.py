"""Read-only French ISBN candidate coverage by numbered tome and edition.

Evidence is incomplete: missing candidate numbers are NOT evidence of
unpublished tomes; UNKNOWN editions are never silently called CLASSIC.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict

from apps.api.app.bnf_batch import connect_database

# Recognize explicit numeric French volume notations only.
VOLUME_PATTERNS = (
    re.compile(r"\b(?:tome|volume|vol\.?|t\.)\s*0*([1-9][0-9]{0,3})\b", re.I),
    re.compile(r"\.\s*0*([1-9][0-9]{0,3})\s*(?:/|\(|$)", re.I),
    re.compile(r":\s*0*([1-9][0-9]{0,3})\s*(?:/|\(|$)", re.I),
)


def volume_from_title(title: str) -> int | None:
    for pattern in VOLUME_PATTERNS:
        match = pattern.search(title or "")
        if match:
            return int(match.group(1))
    return None


def analyze(rows: list[dict]) -> dict:
    grouped: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    unknown = []
    for row in rows:
        kind = row["edition_kind_suggested"] or "UNKNOWN"
        volume = volume_from_title(row["title_fr"])
        if volume is None:
            unknown.append({"isbn13": row["isbn13"], "title": row["title_fr"],
                            "edition": kind})
        else:
            grouped[kind][volume].add(row["isbn13"])
    groups = []
    for kind, volumes in sorted(grouped.items()):
        numbers = sorted(volumes)
        absent = [n for n in range(numbers[0], numbers[-1] + 1) if n not in volumes]
        groups.append({"edition": kind, "numbered_volumes_found": len(numbers),
                       "min_number_found": numbers[0], "max_number_found": numbers[-1],
                       "unseen_numbers_between_min_max": absent,
                       "isbn_candidates_by_volume": {str(n): sorted(volumes[n]) for n in numbers}})
    return {"candidate_rows": len(rows), "edition_groups": groups,
            "unparsed": unknown, "is_exhaustive": False,
            "note": "Numbers absent from BnF candidates may exist in published editions; UNKNOWN is not CLASSIC."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit read-only des tomes/éditions candidats BnF")
    parser.add_argument("--mal-id", type=int, required=True, help="Identifiant MyAnimeList de l'œuvre")
    args = parser.parse_args(argv)
    if args.mal_id <= 0:
        parser.error("--mal-id doit être positif")
    with connect_database() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title FROM manga WHERE source_mal_id=%s", (args.mal_id,))
        manga = cur.fetchone()
        if manga is None:
            parser.error("Œuvre MAL inconnue")
        cur.execute("""SELECT isbn13, title_fr, edition_kind_suggested
                       FROM manga_bnf_candidate WHERE manga_id=%s
                       ORDER BY isbn13""", (manga["id"],))
        rows = list(cur.fetchall())
    print(json.dumps({"mal_id": args.mal_id, "manga": manga["title"],
                      **analyze(rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
