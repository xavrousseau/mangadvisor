"""Contrôle en conditions réelles du contrat explicatif sur PostgreSQL CI jetable.

Aucune écriture : on ne teste ici que les réponses des trois moteurs.
"""
import json
import math
import urllib.parse
import urllib.request

API="http://127.0.0.1:8000"


def get(path, **params):
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    with urllib.request.urlopen(API + path + query, timeout=35) as reply:
        return json.load(reply)


def post(path, payload):
    req=urllib.request.Request(
        API + path, method="POST", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json"},
    )
    with urllib.request.urlopen(req,timeout=45) as reply:
        return json.load(reply)


def verify_result(result, known_source_ids, origin):
    recommendations=result["recommendations"]
    assert recommendations, (origin, result)
    for manga in recommendations:
        info=manga["explanation"]
        assert info["origin"] == origin, info
        assert isinstance(info["source_matches"], list), info
        assert isinstance(info["reference_titles"], list), info
        assert info["score"]["final"] == manga["recommendation_score"], info

        if origin=="library":
            initial=info["score"]["base"]
            bonus=info["score"]["goal_bonus"]
            assert initial is not None and bonus is not None
            assert math.isclose(round(initial + bonus,1), info["score"]["final"],abs_tol=.11)

        detail=get("/mangas/" + str(manga["id"]))
        for source in info["source_matches"]:
            assert source["manga_id"] in known_source_ids, (origin, source)
            source_detail=get("/mangas/" + str(source["manga_id"]))
            for kind in ("genres", "themes", "demographics"):
                source_set=set(source_detail.get(kind) or [])
                target_set=set(detail.get(kind) or [])
                for attribute in source[kind]:
                    assert attribute in source_set & target_set, (origin, kind, attribute)
    print(f"OK: {origin}: {len(recommendations)} suggestions avec sources et scores vérifiés.")


def main():
    similar=get("/recommendations/similar",title="Naruto",limit=5)
    verify_result(similar,{similar["source"]["id"]},"similar")

    manual=post("/recommendations/profile",{
        "liked_titles":["Naruto","Monster"],"limit":5,
        "min_score":6.8,"only_finished":False,
        "exclude_sensitive_mismatches":False,
    })
    verify_result(manual,{m["id"] for m in manual["sources"]},"manual")

    library=post("/recommendations/library",{
        "limit":5,"min_score":6.8,"only_finished":False,
        "exclude_sensitive_mismatches":False,"recommendation_goal":"READ_NEXT",
    })
    verify_result(library,{m["id"] for m in library["positive_sources"]},"library")


if __name__=="__main__":
    main()
