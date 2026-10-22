"""Read-only BnF staged-candidate review; no updates, deletions or approval."""
from __future__ import annotations

import argparse
import json
from collections import Counter

from apps.api.app.bnf_batch import connect_database
from apps.api.app.bnf_candidate_quality import classify_candidate


def review(rows: list[dict], known_titles: list[str]) -> dict:
    classified = [classify_candidate(row, known_titles) for row in rows]
    return {
        "total_staged": len(classified),
        "work_status_counts": dict(Counter(r["work_status"] for r in classified)),
        "language_status_counts": dict(Counter(r["language_status"] for r in classified)),
        "edition_suggested_counts": dict(Counter(r["edition_suggested"] for r in classified)),
        "candidates": sorted(classified, key=lambda row: (
            row["work_status"], row["edition_suggested"],
            str(row["title_fr"]).casefold(), str(row["isbn13"]))),
        "writes_performed": False,
        "work_matched": False,
        "edition_matched": False,
        "notice": "Les donnees sont candidates et restent a verifier pour chaque ISBN.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit BnF lecture seule par oeuvre MAL")
    parser.add_argument("--mal-id", type=int, required=True)
    args = parser.parse_args(argv)
    if args.mal_id <= 0:
        parser.error("--mal-id doit etre positif")
    with connect_database() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id,title,title_english,title_japanese FROM manga WHERE source_mal_id=%s",
            (args.mal_id,),
        )
        manga = cur.fetchone()
        if not manga:
            parser.error("Identifiant MAL inconnu")
        cur.execute(
            """SELECT isbn13,title_fr,publisher_fr,language_recorded,
                      edition_kind_suggested,source_url
               FROM manga_bnf_candidate WHERE manga_id=%s ORDER BY isbn13""",
            (manga["id"],),
        )
        rows = list(cur.fetchall())
    names = [manga[k] for k in ("title", "title_english", "title_japanese")
             if manga.get(k)]
    print(json.dumps({
        "mal_id": args.mal_id,
        "manga": manga["title"],
        **review(rows, names),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
