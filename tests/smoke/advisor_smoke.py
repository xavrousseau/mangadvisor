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
    # The ordinary Docker setup does not download a model: AI endpoint must
    # remain fully functional and clearly disclose guided fallback.
    with urllib.request.urlopen(BASE+"/advisor/ai-status",timeout=20) as health:
        status=json.load(health)
    assert status["mode"]=="guided" and not status["available"],status
    ai_req=urllib.request.Request(
        BASE+"/advisor/ai-message",
        data=json.dumps({"message":"Je cherche un manga d’action","lang":"fr","limit":3}).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(ai_req,timeout=40) as result:
        ai_result=json.load(result)
    assert ai_result["ai_mode"]=="guided",ai_result
    assert ai_result["count"]>0,ai_result
    assert all("mood_matches" in row for row in ai_result["recommendations"]),ai_result

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
    snapshot=second["recommendations"][0]["french_editions"]
    assert snapshot["scope"]=="registered_isbns_only",snapshot
    assert snapshot["registered_isbn_count"]==5,snapshot
    assert snapshot["complete_french_series"] is None,snapshot
    assert snapshot["published_total_known"] is False,snapshot
    assert snapshot["availability_checked"] is False,snapshot
    by_type={x["edition_kind"]:x for x in snapshot["registered_formats"]}
    assert set(by_type)=={"CLASSIC","DELUXE","PERFECT","UNKNOWN"},snapshot
    assert by_type["DELUXE"]["known_volume_numbers"]==[1,2],snapshot
    assert by_type["PERFECT"]["known_volume_numbers"]==[1],snapshot
    assert by_type["CLASSIC"]["known_volume_numbers"]==[3],snapshot
    assert by_type["UNKNOWN"]["known_volume_numbers"]==[1],snapshot
    assert by_type["DELUXE"]["registered_isbn_count"]==2,snapshot
    assert set(book["isbn13"] for book in by_type["DELUXE"]["books_shown"])=={
        "9781234567804","9781234567811"},snapshot
    assert by_type["DELUXE"]["publishers_fr"]==["Éditeur Deluxe fictif"],snapshot
    assert all(x["french_editions"]["registered_isbn_count"]==0
               for x in second["recommendations"][1:]),second

    # The user can change the discovery balance without losing a single filter.
    diversified=request("Surprends-moi avec une sélection inattendue",second["context"])
    assert diversified["context"]["recommendation_balance"]=="EXPLORE",diversified
    assert diversified["context"]["french"]=="PREFER",diversified
    assert diversified["context"]["length"]=="LONG",diversified
    assert diversified["status"]=="results",diversified
    assert diversified["recommendations"][0]["title"]=="Demo CI 08",diversified
    assert all("variety_evidence" in m for m in diversified["recommendations"]),diversified

    close=request("Je veux une sélection très proche de mes goûts",diversified["context"])
    assert close["context"]["recommendation_balance"]=="CLOSE",close
    assert close["context"]["french"]=="PREFER",close
    assert close["recommendations"][0]["title"]=="Demo CI 08",close

    soft_format=request("Je préfère une édition Deluxe",second["context"])
    assert soft_format["context"]["preferred_edition_kind"]=="DELUXE",soft_format
    assert soft_format["context"]["require_edition_kind"] is False,soft_format
    assert soft_format["recommendations"][0]["title"]=="Demo CI 08",soft_format
    assert soft_format["recommendations"][0]["preferred_format_recorded"],soft_format

    required_format=request("Édition Deluxe obligatoire",soft_format["context"])
    assert required_format["context"]["require_edition_kind"] is True,required_format
    assert required_format["count"]==1,required_format
    assert required_format["recommendations"][0]["title"]=="Demo CI 08",required_format

    strict_perfect=request("En édition Perfect uniquement",required_format["context"])
    assert strict_perfect["context"]["preferred_edition_kind"]=="PERFECT",strict_perfect
    assert strict_perfect["count"]==1,strict_perfect
    assert strict_perfect["recommendations"][0]["french_editions"]["registered_formats"],strict_perfect

    none_collectors=request("Collector obligatoire",required_format["context"])
    assert none_collectors["context"]["preferred_edition_kind"]=="COLLECTOR",none_collectors
    assert none_collectors["status"]=="empty" and none_collectors["count"]==0,none_collectors


    narrative=request("Une enquête psychologique, sans horreur et sans gore",second["context"])
    assert narrative["context"]["mood"]=="MYSTERY",narrative
    assert narrative["context"]["avoid_horror"] is True,narrative
    assert narrative["context"]["avoid_gore"] is True,narrative
    assert set(narrative["context"]["narrative_preferences"])=={
        "INVESTIGATION","PSYCHOLOGICAL"},narrative
    assert "sans horreur documentée" in narrative["interpreted_criteria"],narrative
    assert narrative["count"]>0,narrative
    assert all("Horror" not in m["genres"] and "Gore" not in m["themes"]
               for m in narrative["recommendations"]),narrative
    assert all(m["title"]!="Demo CI 28" for m in narrative["recommendations"]),narrative
    assert narrative["recommendations"][0]["title"]=="Demo CI 08",narrative
    matched=narrative["recommendations"][0]["narrative_matches"]
    assert {x["concept"] for x in matched}=={"PSYCHOLOGICAL","INVESTIGATION"},matched
    assert {x["source"] for x in matched}=={"catalog_tag","synopsis_word"},matched
    assert "synopsis" not in narrative["recommendations"][0]

    refined=request("Finalement l'horreur me va",narrative["context"])
    assert refined["context"]["avoid_horror"] is False,refined
    assert refined["context"]["avoid_gore"] is True,refined

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
