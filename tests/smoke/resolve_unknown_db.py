"""CI DISPOSABLE DATABASE ONLY — prove the real BnF-confirmation/CSV lifecycle.

Run within the disposable API container (never against a user's collection).
A fake BnF notice replaces the external lookup only. SQL, API selection, unique
ISBN validation and the import/apply behavior run on actual PostgreSQL.
"""
import json
import urllib.request
from unittest.mock import patch

from apps.api.app.collection import EditionCreate, create_collection_router
from apps.api.app.main import get_connection

API="http://127.0.0.1:8000"


def api(path, data=None):
    payload=json.dumps(data).encode("utf-8") if data is not None else None
    req=urllib.request.Request(
        API+path, data=payload, method="POST" if data is not None else "GET",
        headers={"Content-Type":"application/json"},
    )
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)


with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database() AS db;")
        name=cur.fetchone()["db"]
assert name=="mangadvisor_ci",f"Forbidden outside disposable CI database: {name}"

isbn="9782344074282"
file=f"isbn13;possede;lu\n{isbn};oui;oui\n"
initial=api("/collection/import/preview",{"csv_content":file})
assert initial["unknown"]==1 and initial["matched"]==0,initial
old=next(item for item in api("/library?q=Monster")["items"] if item["title"]=="Monster")

record={
    "isbn13":isbn,"title_fr":"Monster. Tome 1",
    "author_fr":"Naoki Urasawa","publisher_fr":"Éditeur de démonstration CI",
    "release_date_text":"2002",
    "source_name":"BnF — NOTICE SIMULÉE POUR CI UNIQUEMENT",
    "source_url":"https://catalogue.bnf.fr/ark:/12148/cbexample",
    "source_checked_at":"2026-10-18T14:00:00+00:00",
    "verified_isbn":True,"edition_kind_suggested":"UNKNOWN",
}
router=create_collection_router(get_connection)
save=next(route.endpoint for route in router.routes if
          route.path=="/collection/mangas/{manga_id}/editions" and "POST" in route.methods)
with patch("apps.api.app.collection.lookup_bnf",return_value=dict(record)) as lookup:
    linked=save(2,EditionCreate(isbn13=isbn,edition_kind="PERFECT",volume_number=1))
lookup.assert_called_once_with(isbn)
assert linked["edition_kind"]=="PERFECT" and linked["edition_kind_origin"]=="USER_CONFIRMED",linked

# Linking a verified edition does NOT automatically alter an owned/read status.
editions=api("/collection/mangas/2/editions")
matched=next(item for item in editions["editions"] if item["isbn13"]==isbn)
assert not matched["is_owned"] and not matched["is_read"],matched
after=api("/collection/import/preview",{"csv_content":file})
assert after["unknown"]==0 and after["matched"]==1 and after["to_update"]==1,after
assert after["confirmation_token"]!=initial["confirmation_token"],(initial,after)

applied=api("/collection/import/apply",{
    "csv_content":file,"confirmation_token":after["confirmation_token"],
})
assert applied["processed"]==1,applied
updated=api("/collection/mangas/2/editions")
matched=next(item for item in updated["editions"] if item["isbn13"]==isbn)
assert matched["is_owned"] and matched["is_read"],matched

again=api("/collection/import/preview",{"csv_content":file})
assert again["to_update"]==0,again
repeat=api("/collection/import/apply",{
    "csv_content":file,"confirmation_token":again["confirmation_token"],
})
assert repeat["processed"]==1 and repeat["preserved"] is True,repeat

current=next(item for item in api("/library?q=Monster")["items"] if item["title"]=="Monster")
for key in ("library_status","user_score","is_favorite","notes",
            "owned_volumes","read_volumes"):
    assert old[key]==current[key],(key,old[key],current[key])
print("OK CI PostgreSQL: unknown ISBN → confirmed BnF association → recognized CSV → owned/read saved.")
print("OK CI PostgreSQL: reimport preserves all legacy manga library fields.")
