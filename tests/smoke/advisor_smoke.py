"""Real read-only advisor API journey against synthetic CI PostgreSQL."""
import json
import urllib.error
import urllib.request

BASE="http://127.0.0.1:8000"

def request(message, context=None, seen_ids=None, lang="fr"):
    payload={"message":message,"context":context or {},
             "seen_ids":seen_ids or [],"lang":lang,"limit":6}
    req=urllib.request.Request(
        BASE+"/advisor/message",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=40) as result:
        return json.load(result)

def main():
    first=request("Un manga d'action ou d'aventure, plutôt long et terminé")
    assert first["status"]=="results",first
    assert first["count"]>0,first
    assert first["context"]["mood"]=="ACTION",first
    assert first["context"]["length"]=="LONG",first
    assert first["context"]["only_finished"] is True,first
    for row in first["recommendations"]:
        assert row["volumes"]>=13 and row["status"]=="Finished",row
        assert row["title"] not in ("Naruto","Monster","Vinland Saga"),row
        assert row["mood_matches"]["genres"] or row["mood_matches"]["themes"],row

    second=request("Finalement, du mystère, idéalement en français",first["context"])
    assert second["context"]["mood"]=="MYSTERY",second
    assert second["context"]["length"]=="LONG",second
    assert second["context"]["french"]=="PREFER",second
    assert second["status"]=="results",second
    # The one synthetic registered French ISBN should rank high when preferred.
    assert second["recommendations"][0]["title"]=="Demo CI 08",second
    assert second["recommendations"][0]["french_recorded"] is True,second

    strict=request("Français obligatoire",second["context"])
    assert strict["context"]["french"]=="REQUIRE",strict
    assert strict["count"]==1,strict
    assert strict["recommendations"][0]["title"]=="Demo CI 08",strict

    next_page=request("Montre-moi d'autres titres",second["context"],
                      [m["id"] for m in second["recommendations"]])
    assert not (set(m["id"] for m in next_page["recommendations"]) &
                set(m["id"] for m in second["recommendations"])),next_page

    no_mood=request("Je veux un chef-d'œuvre",{})
    assert no_mood["status"]=="clarify",no_mood
    assert not no_mood["recommendations"],no_mood
    unknown=request("Je veux un chef-d'œuvre",second["context"])
    assert unknown["status"]=="clarify",unknown

    with_romance=request("Mais sans romance",second["context"])
    assert with_romance["context"]["avoid_romance"] is True,with_romance
    assert all("Romance" not in row["genres"] for row in with_romance["recommendations"])

    try:
        request("a"*501)
    except urllib.error.HTTPError as exc:
        assert exc.code==422,exc
    else:
        raise AssertionError("Long requests must be bounded")
    print("Advisor context refinement, required vs preferred French evidence, exclusions, safe clarifications and continuation: OK")

if __name__=="__main__":
    main()
