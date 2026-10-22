"""Exercise the 1.1 recommendation quality modes against disposable CI PostgreSQL.

Read-only: no feedback is sent and no library row is modified.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path, **params):
    query = "?" + urllib.parse.urlencode(params) if params else ""
    with urllib.request.urlopen(BASE + path + query, timeout=40) as response:
        return json.load(response)


def post(path, payload):
    request = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def verify_modes(path, payload, known):
    close = post(path, {**payload, "limit":20, "recommendation_balance":"CLOSE"})
    pool = close["recommendations"]
    assert pool, (path, close)
    pool_scores = {m["id"]:m["recommendation_score"] for m in pool}
    default = post(path, {**payload, "limit":8})
    explicit_close = post(path, {**payload, "limit":8, "recommendation_balance":"CLOSE"})
    assert [m["id"] for m in default["recommendations"]] == [
        m["id"] for m in explicit_close["recommendations"]
    ], (path,default,explicit_close)
    assert [m["id"] for m in explicit_close["recommendations"]] == [
        m["id"] for m in pool[:8]
    ], (path, pool)
    for mode in ("BALANCED", "EXPLORE"):
        result = post(path, {**payload, "limit":8, "recommendation_balance":mode})
        recs = result["recommendations"]
        ids = [m["id"] for m in recs]
        assert ids and len(ids)==len(set(ids)), (mode, recs)
        assert not (set(ids) & set(known)), (mode, known, ids)
        assert set(ids) <= set(pool_scores), (mode, ids, pool_scores)
        assert all(m["recommendation_score"] == pool_scores[m["id"]] for m in recs)
        assert all("explanation" in m for m in recs)
        q = result["quality_diagnostic"]
        assert q["mode"] == mode and q["candidate_pool_count"] >= len(recs), q
        assert q["after"]["count"] == len(recs), q
        assert q["after"]["limited_evidence_count"] <= len(recs), q
        print(f"OK {path} {mode}: {len(recs)} candidates; limited={q['after']['limited_evidence_count']}; repeated={q['after']['repeated_overlap_pairs']}")
    return pool


def main():
    all_known = {m["manga_id"] for m in get("/library", limit=100)["items"]}
    assert len(all_known) >= 3, all_known

    profile_params = {
        "liked_titles":["Naruto", "Monster"],
        "min_score":6.8,"only_finished":False,"exclude_sensitive_mismatches":False,
    }
    pool = verify_modes("/recommendations/profile", profile_params, all_known)
    assert not any(m["id"] in all_known for m in pool), all_known

    library_params = {
        "min_score":6.8,"only_finished":False,
        "exclude_sensitive_mismatches":False,
        "recommendation_goal":"READ_NEXT",
    }
    verify_modes("/recommendations/library", library_params, all_known)

    # The three original user goals must all remain operational against the
    # disposable catalogue. None may recommend a series already in the library,
    # whatever its current reading/ownership status.
    for goal in ("SIMILAR_SAFE", "READ_NEXT", "SHORT_FINISHED"):
        response = post("/recommendations/library", {
            **library_params, "recommendation_goal":goal, "limit":20,
            "recommendation_balance":"CLOSE",
        })
        assert response["recommendations"], (goal, response)
        ids = [m["id"] for m in response["recommendations"]]
        assert len(ids) == len(set(ids)), (goal, ids)
        assert not set(ids).intersection(all_known), (goal, ids, all_known)
        print(f"OK library goal {goal}: {len(ids)} distinct suggestions, known manga excluded")

    similar = get("/recommendations/similar",title="Naruto",limit=20)
    assert all(m["id"] not in all_known for m in similar["recommendations"]), similar
    print("OK: exclusion des titres déjà dans la bibliothèque dans les trois moteurs.")


if __name__ == "__main__":
    main()
