"""Meilisearch index of *public catalogue* only. PostgreSQL remains authoritative.

No reading history, personal library data, ownership, ISBN declarations or
private profiles enter the search index. Meilisearch is optional at runtime.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

INDEX = "manga_titles_v1"


def _request(method: str, path: str, payload=None, timeout: float = 3):
    base = "http://%s:%s" % (os.getenv("MEILI_HOST", "meilisearch"), os.getenv("MEILI_PORT", "7700"))
    raw = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + os.getenv("MEILI_MASTER_KEY", ""),
               "Content-Type": "application/json"}
    request = urllib.request.Request(base + path, data=raw, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def search_ids(query: str, *, limit: int = 100, offset: int = 0) -> list[int] | None:
    """Return ranked IDs, or None when search is unavailable/uninitialized.

    Empty list means Meilisearch answered with no matching title; caller may
    additionally fall back to SQL to avoid missing newly imported titles.
    """
    try:
        response = _request("POST", "/indexes/" + INDEX + "/search", {
            "q": query[:120], "limit": min(500, limit), "offset": offset,
            "attributesToRetrieve": ["id"],
        }, timeout=1.5)
        return [int(item["id"]) for item in response.get("hits", [])]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _wait_task(uid: int, *, max_wait: float = 30):
    until = time.monotonic() + max_wait
    while time.monotonic() < until:
        task = _request("GET", "/tasks/%d" % uid, timeout=3)
        if task.get("status") == "succeeded":
            return
        if task.get("status") in ("failed", "canceled"):
            raise RuntimeError("Meilisearch index update failed: " + str(task.get("error")))
        time.sleep(0.25)
    raise TimeoutError("Meilisearch index task timed out")


def sync_catalogue(connect, *, batch: int = 500) -> int:
    """Rebuild the index from public canonical titles and verified aliases only.

    Builds a temporary index before an atomic swap so readers never observe a
    partially rebuilt catalogue. Invoke after PostgreSQL schema initialization.
    """
    staging = INDEX + "_next"
    try:
        _request("GET", "/indexes/" + staging)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    else:
        task = _request("DELETE", "/indexes/" + staging)
        _wait_task(task["taskUid"])
    task = _request("POST", "/indexes", {"uid": staging, "primaryKey": "id"})
    _wait_task(task["taskUid"])
    task = _request("PATCH", "/indexes/" + staging + "/settings", {
        "searchableAttributes": ["title", "title_english", "title_japanese", "aliases", "genres"],
        "filterableAttributes": ["status"],
        "rankingRules": ["words", "typo", "proximity", "attribute", "sort", "exactness"],
        "typoTolerance": {"enabled": True},
    })
    _wait_task(task["taskUid"])
    count = 0
    with connect() as connection:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT m.id,m.title,m.title_english,m.title_japanese,m.status,
                  COALESCE((SELECT array_agg(DISTINCT a.alias)
                            FROM manga_title_alias a WHERE a.manga_id=m.id), ARRAY[]::text[]) AS aliases,
                  COALESCE((SELECT array_agg(DISTINCT g.name)
                            FROM manga_genre mg JOIN genre g ON g.id=mg.genre_id
                            WHERE mg.manga_id=m.id), ARRAY[]::text[]) AS genres
                FROM manga m ORDER BY m.id
            """)
            while True:
                rows = cur.fetchmany(batch)
                if not rows:
                    break
                docs = [dict(row) for row in rows]
                task = _request("POST", "/indexes/" + staging + "/documents", docs, timeout=20)
                _wait_task(task["taskUid"], max_wait=90)
                count += len(docs)
    # An atomic swap keeps the previous full index searchable.
    try:
        _request("GET", "/indexes/" + INDEX)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        task = _request("POST", "/indexes", {"uid": INDEX, "primaryKey": "id"})
        _wait_task(task["taskUid"])
    task = _request("POST", "/swap-indexes", [{"indexes": [INDEX, staging]}])
    _wait_task(task["taskUid"])
    task = _request("DELETE", "/indexes/" + staging)
    _wait_task(task["taskUid"])
    return count


if __name__ == "__main__":
    from apps.api.app.main import get_connection
    amount = sync_catalogue(get_connection)
    print("Meilisearch: %d public manga indexed" % amount)
