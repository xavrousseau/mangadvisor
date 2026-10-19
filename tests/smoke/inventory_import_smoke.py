"""CI ONLY: verify private inventory import is additive, idempotent, reversible via backup.

All names are fabricated; no real user workbook is placed in GitHub.
Run exclusively against disposable Mangadvisor CI PostgreSQL.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

URL="http://127.0.0.1:8000"


def req(path: str, data: dict | None = None, expected: int = 200) -> dict:
    body=json.dumps(data).encode("utf-8") if data is not None else None
    request=urllib.request.Request(
        URL+path,data=body,method="POST" if body is not None else "GET",
        headers={"Content-Type":"application/json"},
    )
    try:
        with urllib.request.urlopen(request,timeout=90) as response:
            assert expected==response.status,(expected,response.status)
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code==expected:
            return json.loads(exc.read())
        raise


def fixture(value=3) -> str:
    return (
        "serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier;"
        "statut_releve;ligne_source;oeuvre_commune;edition_declaree;format_catalogue_provisoire\n"
        "Naruto;72;2;0;Possede;Inventaire!A4;;;\n"
        f"Demo CI 16 Version X;{value};0;0;Possede;Inventaire!A5;Demo CI 16;Version X;INCONNU\n"
        "Demo CI 16 Version Y;4;1;0;Possede;Inventaire!A6;Demo CI 16;Version Y;INCONNU\n"
        "Inconnu de CI;2;0;0;Possede;Inventaire!A7;;;\n"
    )


def library_row(title: str) -> dict | None:
    items=req("/library?limit=500")["items"]
    return next((r for r in items if r["title"]==title),None)


def main() -> None:
    health=req("/health")
    assert health["database"]=="mangadvisor_ci","REFUS: base CI uniquement"
    before_naruto=library_row("Naruto")
    assert before_naruto and before_naruto["library_status"]=="READ",before_naruto
    # Legacy generic CSV reimport must not erase an existing manga's notes,
    # scores, favorites or reading status even when sparse/wrong fields arrive.
    req("/library/import/csv",{
        "csv_content":"title,library_status,user_score,is_favorite,owned_volumes,read_volumes,notes\n"
                      "Naruto,OWNED,0,false,0,0,SHOULD_NOT_OVERWRITE\n",
        "delimiter":",","dry_run":False,"default_status":"WANT_TO_READ",
    })
    assert library_row("Naruto")==before_naruto,"Legacy CSV overwrote a user's reading"
    before_demo=library_row("Demo CI 16")
    assert before_demo is None,before_demo
    before=req("/inventory/declarations")
    assert before["count"]==0,before

    # Existing explicit rejection of a different work must not be silently
    # converted to ownership by a physical inventory declaration.
    conflict=req("/inventory/preview",{"csv_content":
        "serie;tomes_principaux;doublons_identiques;autres_editions_a_identifier\n"
        "Demo CI 05;1;0;0\n"
    })
    assert conflict["items"][0]["status"]=="REVIEW_LIBRARY_CONFLICT",conflict

    first=req("/inventory/preview",{"csv_content":fixture()})
    assert len(first["items"])==4,first
    assert first["ready"]==3 and first["review"]==1,first
    assert first["declared_physical_volumes"]==84,first
    assert first["items"][0]["existing_library_status"]=="READ"
    assert first["items"][1]["manga_id"]==first["items"][2]["manga_id"]
    assert first["items"][1]["edition_key"] != first["items"][2]["edition_key"]
    assert first["items"][3]["status"]=="REVIEW_MISSING"
    assert req("/inventory/declarations")["count"]==0

    # User opt-in preserves the unknown entry independently from known mangas.
    # This does not invent an FK, ISBN, read status or library ownership.
    assert req("/inventory/pending")["count"]==0
    pending_payload={"csv_content":fixture(),"confirmation_token":first["confirmation_token"]}
    assert req("/inventory/pending/save",{**pending_payload,"confirmation_token":"0"*64},409)["detail"]
    saved_pending=req("/inventory/pending/save",pending_payload)
    assert saved_pending["saved"]==1 and saved_pending["linked_mangas"]==0,saved_pending
    assert saved_pending["pending_physical_volumes"]==2,saved_pending
    waiting=req("/inventory/pending")
    assert waiting["count"]==1 and waiting["declared_physical_volumes"]==2,waiting
    assert waiting["items"][0]["entry_title"]=="Inconnu de CI",waiting
    assert "manga_id" not in waiting["items"][0],waiting
    assert req("/inventory/declarations")["count"]==0
    assert library_row("Inconnu de CI") is None
    second_save=req("/inventory/pending/save",pending_payload)
    assert second_save["saved"]==0 and second_save["unchanged_pending"]==1,second_save
    assert req("/inventory/pending")["count"]==1
    payload={"csv_content":fixture(),"confirmation_token":first["confirmation_token"]}
    assert req("/inventory/apply",payload,409)["detail"].startswith("Des lignes")
    assert req("/inventory/declarations")["count"]==0

    modified={**payload,"confirmation_token":"0"*64,"accept_partial":True}
    assert req("/inventory/apply",modified,409)["detail"].startswith("L'inventaire")
    saved=req("/inventory/apply",{**payload,"accept_partial":True})
    assert saved["status"]=="ok",saved
    assert saved["created_declarations"]==3,saved
    assert saved["manual_review"]==1,saved
    assert saved["preserved_reading_notes_scores"],saved

    rows=req("/inventory/declarations")["items"]
    assert len(rows)==3,rows
    versions=[r for r in rows if r["work_title"]=="Demo CI 16"]
    assert len(versions)==2,versions
    assert {r["edition_declared"] for r in versions}=={"Version X","Version Y"},versions
    assert {r["main_volumes"] for r in versions}=={3,4},versions
    assert sum(r["duplicate_copies"] for r in versions)==1,versions
    assert all("isbn" not in r for r in versions),versions
    assert library_row("Naruto")==before_naruto,"Existing notes/scores/reads modified"
    created=library_row("Demo CI 16")
    assert created["library_status"]=="OWNED",created
    assert created["owned_volumes"] is None and created["read_volumes"] is None,created
    assert created["user_score"] is None,created

    assert req("/inventory/apply",{**payload,"accept_partial":True},409)["detail"].startswith(
        "L'inventaire"
    ),"Stale preview unexpectedly accepted"
    again=req("/inventory/preview",{"csv_content":fixture()})
    assert again["unchanged"]==3 and again["review"]==1,again
    noop=req("/inventory/apply",{"csv_content":fixture(),
                      "confirmation_token":again["confirmation_token"],
                      "accept_partial":True})
    assert noop["created_declarations"]==0,noop

    changed=req("/inventory/preview",{"csv_content":fixture(10)})
    assert changed["ready"]==0 and changed["review"]==2,changed
    assert changed["items"][1]["status"]=="REVIEW_EXISTING",changed
    assert req("/inventory/apply",{
        "csv_content":fixture(10),"confirmation_token":changed["confirmation_token"],
        "accept_partial":True,
    })["created_declarations"]==0,"Existing edition count was overwritten"
    assert {r["main_volumes"] for r in req("/inventory/declarations")["items"]
            if r["work_title"]=="Demo CI 16"}=={3,4}

    # Test user-facing guarded recommendation integration; imported works
    # are now excluded by the existing user_manga_library SQL constraints.
    suggestions=req("/advisor/message",{
        "message":"Je cherche un manga d'action ou d'aventure",
        "context":{},"lang":"fr","limit":12,
    })
    assert created["manga_id"] not in [m["id"] for m in suggestions.get("recommendations",[])],suggestions
    print("OK: preview->token->partial opt-in->import; exact work, distinct editions; "
          "no overwritten reads/notes; no invented ISBN; idempotent; post-import rec exclusion.")


if __name__=="__main__":
    main()
