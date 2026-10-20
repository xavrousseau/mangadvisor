"""CI-only live API regression: an owned physical work stays excluded even without library status.

Only runs against a disposable PostgreSQL database; never imports personal files.
"""
from __future__ import annotations

import json
import os
import urllib.request

if os.getenv("POSTGRES_DB") != "mangadvisor_ci":
    raise SystemExit("REFUS : test de modification uniquement sur la base jetable mangadvisor_ci.")

from apps.api.app.main import get_connection  # noqa: E402


def api(path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        "http://127.0.0.1:8000" + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def candidates() -> list[tuple[str, str, dict | None]]:
    return [
        ("guided", "/discovery/mood", {
            "mood": "ACTION", "length": "ANY", "min_score": 0,
            "use_library": False, "limit": 12,
        }),
        ("similar", "/recommendations/similar?title=Naruto&limit=12", None),
        ("profile", "/recommendations/profile", {
            "liked_titles": ["Naruto", "Monster"], "min_score": 0, "limit": 12,
        }),
        ("advisor", "/advisor/message", {
            "message": "Je cherche des mangas d'action",
            "context": {"min_score": 0}, "lang": "fr", "limit": 12,
        }),
    ]


def main() -> None:
    health = api("/health")
    assert health.get("database") == "mangadvisor_ci", health
    results = [(key, path, payload, api(path, payload)) for key, path, payload in candidates()]
    selected: dict[str, int] = {}
    for key, path, payload, result in results:
        rows = result.get("recommendations") or []
        if rows:
            selected[key] = int(rows[0]["id"])
    assert selected.get("guided") is not None, "CI fixture must provide guided-discovery candidates"
    assert len(selected) >= 3, f"Insufficient live recommendations to test physical exclusion: {selected}"
    ids = sorted(set(selected.values()))
    inserted: list[int] = []
    try:
        with get_connection() as connection:
            with connection.cursor() as cur:
                for manga_id in ids:
                    cur.execute(
                        "SELECT 1 FROM user_manga_library WHERE user_id=1 AND manga_id=%s",
                        (manga_id,),
                    )
                    assert cur.fetchone() is None, f"Chosen manga {manga_id} already in the library"
                    cur.execute(
                        """INSERT INTO user_manga_inventory_declaration (
                            user_id,manga_id,edition_key,edition_declared,entry_title,
                            main_volumes,duplicate_copies,other_editions_unknown
                        ) SELECT 1,id,'CI_PHYSICAL_OWNED','CI synthetic edition',
                                 title,1,0,0 FROM manga WHERE id=%s
                        ON CONFLICT (user_id,manga_id,edition_key) DO NOTHING
                        RETURNING manga_id""",
                        (manga_id,),
                    )
                    assert cur.fetchone() is not None, f"CI declaration already exists for {manga_id}"
                    inserted.append(manga_id)
        # Explicit regression: owning a physical edition is independent of
        # user_manga_library, e.g. after removing a reading-tracking row.
        for key, path, payload, before in results:
            after = api(path, payload)
            returned = {int(item["id"]) for item in after.get("recommendations") or []}
            assert returned.isdisjoint(ids), {
                "mode": key, "physically_owned": ids, "returned": sorted(returned),
            }
        print("Physical inventory exclusions verified in: "
              + ", ".join(key for key, _, _, _ in results)
              + " (without reading-library rows).")
    finally:
        with get_connection() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_manga_inventory_declaration "
                    "WHERE user_id=1 AND edition_key='CI_PHYSICAL_OWNED' "
                    "AND manga_id=ANY(%s::integer[])",
                    (inserted,),
                )


if __name__ == "__main__":
    main()
