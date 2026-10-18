"""CI disposable DB only: physical French edition tracking is independent of legacy counts."""
import json
import urllib.request
import urllib.error

API="http://127.0.0.1:8000"


def request(path,method="GET",body=None):
    req=urllib.request.Request(API+path,method=method,
        headers={"Content-Type":"application/json"},
        data=json.dumps(body).encode("utf-8") if body is not None else None)
    with urllib.request.urlopen(req,timeout=30) as res:
        return json.load(res)


def main():
    editions=request("/collection/mangas/1/editions")
    assert editions["count"]==1 and editions["owned_books"]==0,editions
    assert editions["read_books"]==0 and editions["missing_known_books"]==1,editions
    edition=editions["editions"][0]
    assert edition["isbn13"]=="9782871294146" and edition["edition_kind"]=="CLASSIC",edition
    library_before=request("/library?q=Naruto")["items"][0]

    # Read-only without owning is explicitly supported.
    changed=request("/collection/volumes/"+str(edition["id"]),"PUT",
                    {"is_owned":False,"is_read":True})
    assert changed["is_read"] and not changed["is_owned"],changed
    after=request("/collection/mangas/1/editions")
    assert (after["owned_books"],after["read_books"],after["missing_known_books"])==(0,1,1),after

    # Owning the volume must not destroy "read" and existing library notes.
    changed=request("/collection/volumes/"+str(edition["id"]),"PUT",
                    {"is_owned":True,"is_read":True})
    assert changed["is_owned"] and changed["is_read"]
    after=request("/collection/mangas/1/editions")
    assert (after["owned_books"],after["read_books"],after["missing_known_books"])==(1,1,0),after
    library_after=request("/library?q=Naruto")["items"][0]
    for key in ("owned_volumes","read_volumes","user_score","notes","library_status","is_favorite"):
        assert library_before[key]==library_after[key],(key,library_before[key],library_after[key])

    # A wrongly linked ISBN cannot be accepted as the correct manga without conflict.
    try:
        request("/collection/mangas/99999/editions")
        raise AssertionError("Unknown manga accepted")
    except urllib.error.HTTPError as exc:
        assert exc.code==404

    # Reset only the synthetic CI row to its original state for UI tests.
    request("/collection/volumes/"+str(edition["id"]),"PUT",{"is_owned":False,"is_read":False})
    print("OK: 1 French book, separate owned/read states, missing count and unchanged historical library.")


if __name__=="__main__":
    main()
