"""CI ONLY: test feedback persistence and ranking exclusions against disposable PostgreSQL.

Never run this against a personal Mangadvisor database.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

API = "http://127.0.0.1:8000"


def get(path, **params):
    suffix = "?" + urllib.parse.urlencode(params) if params else ""
    with urllib.request.urlopen(API + path + suffix, timeout=30) as reply:
        return json.load(reply)


def post(path, data):
    request = urllib.request.Request(
        API + path,
        method="POST",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as reply:
        return json.load(reply)


def library_item(title):
    records = get("/library", q=title, limit=100)["items"]
    return next(record for record in records if record["title"] == title)


def main():
    # Interested: the new status is reused by the existing library model.
    interest = post("/recommendations/feedback", {"manga_id": 33, "action": "INTERESTED"})
    assert interest["library_status"] == "WANT_TO_READ", interest
    assert library_item("Demo CI 33")["library_status"] == "WANT_TO_READ"
    positive = post("/recommendations/library", {
        "limit": 20, "min_score": 6.8, "only_finished": False,
        "exclude_sensitive_mismatches": False,
        "recommendation_goal": "SIMILAR_SAFE",
    })
    assert any(row["id"] == 33 for row in positive["positive_sources_available"]), positive

    # Already read: preserve rating and number of volumes from the existing record.
    old = library_item("Vinland Saga")
    assert old["library_status"] == "READING" and old["read_volumes"] == 3, old
    read = post("/recommendations/feedback", {"manga_id": old["manga_id"], "action": "ALREADY_READ"})
    assert read["library_status"] == "READ", read
    updated = library_item("Vinland Saga")
    for key in ("user_score", "owned_volumes", "read_volumes", "notes", "is_favorite"):
        assert updated[key] == old[key], (key, old[key], updated[key])
    assert updated["library_status"] == "READ"

    # An unrelated negative reaction must not erase an existing reading history.
    try:
        post("/recommendations/feedback", {"manga_id": old["manga_id"], "action": "NOT_FOR_ME"})
        raise AssertionError("Unexpected overwrite of a READ entry")
    except urllib.error.HTTPError as exc:
        assert exc.code == 409, exc.code
    assert library_item("Vinland Saga")["library_status"] == "READ"

    # Exclusion must be enforced in SQL before LIMIT, not hidden only in the web UI.
    similar = get("/recommendations/similar", title="Naruto", limit=20)
    candidates = [x for x in similar["recommendations"] if int(x["id"]) not in (1, 2, 3, 33)]
    assert candidates, similar
    unwanted_id = candidates[0]["id"]
    excluded = post("/recommendations/feedback", {"manga_id": unwanted_id, "action": "NOT_FOR_ME"})
    assert excluded["library_status"] == "NOT_INTERESTED"
    again = get("/recommendations/similar", title="Naruto", limit=20)
    assert unwanted_id not in [x["id"] for x in again["recommendations"]], again

    prof = post("/recommendations/profile", {
        "liked_titles": ["Naruto", "Monster"], "limit": 20,
        "min_score": 6.8, "only_finished": False,
        "exclude_sensitive_mismatches": False,
    })
    assert unwanted_id not in [x["id"] for x in prof["recommendations"]], prof

    library_result = post("/recommendations/library", {
        "limit": 20, "min_score": 6.8, "only_finished": False,
        "exclude_sensitive_mismatches": False,
        "recommendation_goal": "READ_NEXT",
    })
    assert unwanted_id not in [x["id"] for x in library_result["recommendations"]], library_result

    print("OK: interested/read/dislike persisted; notes preserved; explicit rejection protected;")
    print("OK: disliked title excluded in similar, profile and library recommendations.")


if __name__ == "__main__":
    main()
