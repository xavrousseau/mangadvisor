"""CI only: exact ISBN batch CSV, non-destructive state merge, reconciliation."""
from __future__ import annotations
import json
import urllib.error
import urllib.request

BASE="http://127.0.0.1:8000"


def req(path, body=None):
    request=urllib.request.Request(
        BASE+path,method="POST" if body is not None else "GET",
        headers={"Content-Type":"application/json"},
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    with urllib.request.urlopen(request,timeout=30) as result:
        return json.load(result)


def main():
    old=req("/library?q=Naruto")["items"][0]
    editions=req("/collection/mangas/1/editions")
    assert editions["count"]==1,editions
    book=editions["editions"][0]
    # The browser smoke earlier may already mark Naruto as owned.
    # READ stays false and this CSV adds that precise fact without erasing OWNED.
    assert not book["is_read"],book
    csv="isbn13;possede;lu\n9782871294146;oui;non\n9782871294146;non;oui\n9782344074282;oui;non\n9782871294141;oui;oui\n"
    preview=req("/collection/import/preview",{"csv_content":csv})
    assert preview["matched"]==1 and preview["unknown"]==1,preview
    assert preview["duplicate_rows"]==1,preview
    assert len(preview["errors"])==1,preview
    assert preview["to_update"]==1,preview
    book_before=req("/collection/mangas/1/editions")["editions"][0]
    assert book_before["is_owned"]==book["is_owned"] and not book_before["is_read"]

    try:
        req("/collection/import/apply",{"csv_content":csv,
            "confirmation_token":"0"*64})
        raise AssertionError("Unreviewed CSV accepted!")
    except urllib.error.HTTPError as exc:
        assert exc.code==409,exc.code

    applied=req("/collection/import/apply",{"csv_content":csv,
        "confirmation_token":preview["confirmation_token"]})
    assert applied["processed"]==1 and applied["unknown"]==1,applied
    now=req("/collection/mangas/1/editions")["editions"][0]
    assert now["is_owned"] and now["is_read"],now
    after=req("/library?q=Naruto")["items"][0]
    for field in ("library_status","user_score","is_favorite",
                  "notes","owned_volumes","read_volumes"):
        assert after[field]==old[field],(field,old[field],after[field])

    reconcile=req("/collection/reconciliation")
    assert reconcile["count"]>=3,reconcile
    naruto=next(row for row in reconcile["items"] if row["manga_id"]==1)
    assert naruto["known_books"]==1 and naruto["owned_books"]==1 and naruto["read_books"]==1
    assert reconcile["isbn_totals"]["owned"]>=1
    assert reconcile["legacy_totals"]["owned"]==sum(
        int(row["legacy_owned"] or 0) for row in reconcile["items"]
    )

    # Repeated upload is idempotent; a negative status cannot erase owned/read.
    csv_negative="isbn13;owned;read\n9782871294146;no;no\n"
    negative_preview=req("/collection/import/preview",{"csv_content":csv_negative})
    assert negative_preview["to_update"]==0,negative_preview
    repeat=req("/collection/import/apply",{"csv_content":csv_negative,
        "confirmation_token":negative_preview["confirmation_token"]})
    assert repeat["processed"]==0,repeat
    final=req("/collection/mangas/1/editions")["editions"][0]
    assert final["is_owned"] and final["is_read"],final

    print("OK: CSV preview+approval, duplicates, invalid and unknown ISBN skipped.")
    print("OK: legacy fields remain unchanged and reconciliation stays read-only.")


if __name__=="__main__":
    main()
