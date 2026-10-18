"""Read-only PostgreSQL-backed discovery checks on CI's disposable catalog."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/discovery/mood"

def post(data):
    req = urllib.request.Request(
        BASE, data=json.dumps(data).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    query={"mood":"MYSTERY","length":"LONG","only_finished":False,
           "use_library":True,"min_score":6.5,"limit":8}
    personal=post(query)
    assert personal["personalized"] is True, personal
    assert personal["source"] == "catalog_and_library", personal
    assert personal["recommendations"], personal
    assert personal["count"] == len(personal["recommendations"]), personal
    assert len({m["id"] for m in personal["recommendations"]}) == personal["count"]
    for m in personal["recommendations"]:
        assert m["volumes"] >= 13, m
        assert m["title"] not in {"Naruto","Monster","Vinland Saga"}, m
        assert set(m["mood_matches"]["genres"]) <= set(m["genres"]), m
        assert set(m["mood_matches"]["themes"]) <= set(m["themes"]), m
        assert m["mood_matches"]["genres"] or m["mood_matches"]["themes"], m
        assert m["ranking_score"] is None
    catalog=post({**query,"use_library":False})
    assert catalog["personalized"] is False, catalog
    assert catalog["source"] == "catalog_only", catalog
    assert all(not (m["affinity_matches"]["genres"] or
                    m["affinity_matches"]["themes"])
               for m in catalog["recommendations"])
    assert post({**query,"length":"SHORT"})["recommendations"] == []
    finished=post({**query,"only_finished":True})
    assert finished["recommendations"], finished
    assert all(m["status"] == "Finished" for m in finished["recommendations"])
    try:
        post({**query,"mood":"MOOD_INVENTED"})
    except urllib.error.HTTPError as exc:
        assert exc.code == 422
    else:
        raise AssertionError("Unsupported mood must be rejected")
    print("Guided discovery: catalog evidence, taste overlap, status, length and read-only selections OK")


if __name__ == "__main__":
    main()
