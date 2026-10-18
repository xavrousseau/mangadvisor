"""Verify explicit BnF confirmation never silently links a book to the wrong manga."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from apps.api.app.collection import create_collection_router, EditionCreate


RECORD = {
    "isbn13":"9782871294146","title_fr":"Naruto. Tome 1",
    "publisher_fr":"Kana","author_fr":"Masashi Kishimoto",
    "release_date_text":"2002","source_name":"Bibliothèque nationale de France",
    "source_url":"https://catalogue.bnf.fr/ark:/12148/cb12345678x",
    "source_checked_at":"2026-10-18T12:00:00+00:00",
    "verified_isbn":True,"edition_kind_suggested":"UNKNOWN",
}


class Cursor:
    def __init__(self, *, manga_exists=True, isbn_exists=False):
        self.manga_exists=manga_exists
        self.isbn_exists=isbn_exists
        self.sql=""
        self.data={}
        self.calls=[]

    def __enter__(self):
        return self
    def __exit__(self,*_):
        return False
    def execute(self,sql,params):
        self.sql=sql.strip()
        self.data=params
        self.calls.append(self.sql)
    def fetchone(self):
        if self.sql.startswith("SELECT id FROM manga"):
            return {"id":1} if self.manga_exists else None
        if self.sql.startswith("SELECT id, manga_id FROM manga_fr_edition"):
            return {"id":3,"manga_id":2} if self.isbn_exists else None
        if self.sql.startswith("INSERT INTO manga_fr_edition"):
            return {"id":101}
        raise AssertionError("Unexpected SQL: "+self.sql[:100])


class Conn:
    def __init__(self,**kwargs):
        self.cur=Cursor(**kwargs)
        self.commits=0
    def __enter__(self):
        return self
    def __exit__(self,*_):
        return False
    def cursor(self):
        return self.cur
    def commit(self):
        self.commits+=1


def endpoint(factory):
    router=create_collection_router(factory)
    return next(r.endpoint for r in router.routes
        if r.path=="/collection/mangas/{manga_id}/editions"
        and "POST" in r.methods)


class CollectionRouteTests(unittest.TestCase):
    def test_link_only_after_source_confirmation(self):
        conn=Conn()
        handler=endpoint(lambda:conn)
        with patch("apps.api.app.collection.lookup_bnf",return_value=dict(RECORD)) as fetch:
            out=handler(1,EditionCreate(isbn13="9782871294146",
                                        edition_kind="DELUXE",volume_number=2))
        fetch.assert_called_once_with("9782871294146")
        self.assertEqual(out["id"],101)
        self.assertEqual(out["edition_kind"],"DELUXE")
        self.assertEqual(out["edition_kind_origin"],"USER_CONFIRMED")
        self.assertEqual(conn.cur.data["manga_id"],1)
        self.assertEqual(conn.cur.data["source_url"],RECORD["source_url"])
        self.assertEqual(conn.commits,1)

    def test_rejects_duplicate_isbn_without_silent_reassignment(self):
        conn=Conn(isbn_exists=True)
        handler=endpoint(lambda:conn)
        with patch("apps.api.app.collection.lookup_bnf",return_value=dict(RECORD)):
            with self.assertRaises(HTTPException) as caught:
                handler(1,EditionCreate(isbn13="9782871294146",
                                       edition_kind="CLASSIC",volume_number=1))
        self.assertEqual(caught.exception.status_code,409)
        self.assertFalse(any(sql.startswith("INSERT") for sql in conn.cur.calls))
        self.assertEqual(conn.commits,0)

    def test_unknown_manga_cannot_receive_an_edition(self):
        conn=Conn(manga_exists=False)
        handler=endpoint(lambda:conn)
        with patch("apps.api.app.collection.lookup_bnf",return_value=dict(RECORD)):
            with self.assertRaises(HTTPException) as caught:
                handler(999,EditionCreate(isbn13="9782871294146",
                                         edition_kind="CLASSIC",volume_number=1))
        self.assertEqual(caught.exception.status_code,404)
        self.assertEqual(conn.commits,0)

    def test_no_source_record_means_no_write(self):
        conn=Conn()
        handler=endpoint(lambda:conn)
        with patch("apps.api.app.collection.lookup_bnf",return_value=None):
            with self.assertRaises(HTTPException) as caught:
                handler(1,EditionCreate(isbn13="9782871294146",
                                        edition_kind="CLASSIC",volume_number=1))
        self.assertEqual(caught.exception.status_code,404)
        self.assertEqual(conn.cur.calls,[])


if __name__=="__main__":
    unittest.main()
