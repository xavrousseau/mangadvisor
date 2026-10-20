"""Manual catalogue-work matching keeps edition, counts, provenance and books separate."""
from __future__ import annotations

import hashlib
import unittest
from fastapi import HTTPException
from apps.api.app.inventory_import import SCHEMA
from apps.api.app.inventory_resolution import (
    _review_token, edition_key_for_pending, default_search_term,
    create_pending_resolution_router, MANGA_SQL, EXISTING_SQL, REJECTED_SQL,
    PENDING_SQL,
)


PENDING = {
    "source_key":"Inventaire!A29",
    "entry_title":"Dragon Ball (34 tomes)",
    "source_reference":"Inventaire!A29",
    "work_declared":"Dragon Ball",
    "edition_declared":"Deluxe",
    "format_hint":"PERFECT_A_VERIFIER",
    "main_volumes":34,
    "duplicate_copies":0,
    "other_editions_unknown":0,
    "review_status":"REVIEW_MISSING",
    "candidate_ids":[],
    "content_sha256":"a"*64,
}
MANGA = {
    "id":15,"title":"Dragon Ball",
    "title_english":"Dragon Ball","title_japanese":None,
    "source_mal_id":42,"manga_type":"Manga","volumes":42,
}


class DummyCursor:
    def __init__(self, db):
        self.db=db
        self.last_sql=""
        self.last_params=None
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.last_sql=sql
        self.last_params=params
        self.db.queries.append((sql,params))
    def fetchone(self):
        sql=self.last_sql
        if "FROM user_manga_inventory_pending" in sql:
            return self.db.pending
        if "FROM manga m WHERE m.id" in sql:
            return self.db.manga
        if "FROM user_manga_inventory_declaration" in sql:
            return self.db.existing
        if "FROM user_manga_library" in sql:
            return self.db.rejected
        if "INSERT INTO" in sql or "DELETE FROM" in sql:
            return {"source_key":"Inventaire!A29"}
        return None
    def fetchall(self):
        if "LIMIT 12" in self.last_sql and "FROM manga m" in self.last_sql:
            return self.db.candidates
        if "FROM user_manga_inventory_declaration" in self.last_sql:
            return [self.db.existing] if self.db.existing else []
        return []


class DummyConnection:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cursor(self):return DummyCursor(self.db)
    def commit(self):self.db.commits+=1


class DummyDb:
    def __init__(self,pending=None,manga=None,existing=None,rejected=None):
        self.pending=pending if pending is not None else dict(PENDING)
        self.manga=manga if manga is not None else dict(MANGA)
        self.existing=existing
        self.rejected=rejected
        self.candidates=[dict(MANGA,suggestion_kind="EXACT_TITLE")]
        self.queries=[]
        self.commits=0
    def __call__(self):return DummyConnection(self)


class PendingResolutionTests(unittest.TestCase):
    def endpoints(self,db):
        router=create_pending_resolution_router(db)
        return {route.path:route.endpoint for route in router.routes}

    def test_edition_separation_by_original_owner_label_not_format_guess(self):
        self.assertEqual(edition_key_for_pending(PENDING),"deluxe")
        self.assertEqual(edition_key_for_pending({**PENDING,"edition_declared":"Pastel"}),"pastel")
        self.assertNotEqual(edition_key_for_pending(PENDING),
                            edition_key_for_pending({**PENDING,"edition_declared":"Pastel"}))
        self.assertEqual(edition_key_for_pending({**PENDING,"edition_declared":None}),
                         "__UNSPECIFIED__")
        self.assertEqual(default_search_term(PENDING),"Dragon Ball")
        self.assertEqual(default_search_term({
            **PENDING,"work_declared":None
        }),"Dragon Ball")
        self.assertIn("CREATE TABLE IF NOT EXISTS user_manga_inventory_resolution",SCHEMA)
        self.assertIn("original_declaration JSONB NOT NULL",SCHEMA)

    def test_preview_is_read_only_and_hash_covers_source_and_manga_identity(self):
        from apps.api.app.inventory_import import PendingResolvePreview
        db=DummyDb()
        preview=self.endpoints(db)["/inventory/pending/resolve/preview"](
            PendingResolvePreview(source_key="Inventaire!A29",manga_id=15)
        )
        self.assertEqual(preview["source"]["main_volumes"],34)
        self.assertEqual(preview["source"]["edition_declared"],"Deluxe")
        self.assertEqual(preview["manga"]["id"],15)
        self.assertEqual(preview["edition_key"],"deluxe")
        self.assertEqual(len(preview["confirmation_token"]),64)
        self.assertNotIn("_pending",preview)
        self.assertTrue(all("INSERT " not in q and "DELETE " not in q
                            for q,_ in db.queries))
        self.assertNotEqual(_review_token(PENDING,MANGA,1),
                            _review_token({**PENDING,"content_sha256":"b"*64},MANGA,1))
        self.assertNotEqual(_review_token(PENDING,MANGA,1),
                            _review_token(PENDING,{**MANGA,"title":"Other Dragon Ball"},1))
        self.assertNotEqual(_review_token(PENDING,MANGA,1),
                            _review_token(PENDING,MANGA,2))

    def test_source_title_search_only_returns_candidates_never_links(self):
        db=DummyDb()
        find=self.endpoints(db)["/inventory/pending/candidates"]
        result=find(source_key="Inventaire!A29",q=None)
        self.assertEqual(result["query"],"Dragon Ball")
        self.assertFalse(result["automatic_association"])
        self.assertEqual(result["items"][0]["id"],15)
        query=next((p for q,p in db.queries if "ILIKE" in q),None)
        self.assertEqual(query["pattern"],"%Dragon Ball%")
        db.queries.clear()
        result=find(source_key="Inventaire!A29",q=r"100%_\\")
        query=next((p for q,p in db.queries if "ILIKE" in q),None)
        self.assertIn(r"\%",query["pattern"])
        self.assertIn(r"\_",query["pattern"])
        self.assertEqual(result["query"],r"100%_\\")
        self.assertFalse(any("INSERT " in q for q,_ in db.queries))

    def test_confirm_requires_review_token_and_manual_acknowledgment(self):
        from apps.api.app.inventory_import import PendingResolveConfirm
        db=DummyDb()
        endpoint=self.endpoints(db)["/inventory/pending/resolve"]
        key="Inventaire!A29"
        good=_review_token(PENDING,MANGA,1)
        for token,ack in [("0"*64,True),(good,False)]:
            with self.subTest(token=token,ack=ack):
                with self.assertRaises(HTTPException):
                    endpoint(PendingResolveConfirm(source_key=key,manga_id=15,
                        confirmation_token=token,acknowledge_work_and_edition=ack))
        self.assertFalse(any("INSERT INTO" in q for q,_ in db.queries))
        ok=endpoint(PendingResolveConfirm(source_key=key,manga_id=15,
            confirmation_token=good,acknowledge_work_and_edition=True))
        self.assertEqual(ok["status"],"confirmed")
        self.assertFalse(ok["isbn_verified"])
        self.assertFalse(ok["reading_status_modified"])
        self.assertFalse(ok["progress_modified"])
        names=[q for q,_ in db.queries]
        inserts=[q for q in names if "INSERT INTO" in q]
        self.assertEqual(len(inserts),2)
        self.assertTrue(any("user_manga_inventory_declaration" in q for q in inserts))
        self.assertTrue(any("user_manga_inventory_resolution" in q for q in inserts))
        self.assertTrue(any("DELETE FROM user_manga_inventory_pending" in q for q in names))
        self.assertFalse(any("UPDATE user_manga_library" in q or
                             "INSERT INTO manga_fr_edition" in q or
                             "INSERT INTO user_manga_volume" in q
                             for q in names))
        self.assertEqual(db.commits,1)
        declaration=next(p for q,p in db.queries
                         if "INSERT INTO user_manga_inventory_declaration" in q)
        self.assertEqual(declaration["edition_key"],"deluxe")
        self.assertEqual(declaration["main_volumes"],34)
        self.assertEqual(declaration["duplicate_copies"],0)

    def test_existing_edition_is_visible_and_requires_explicit_no_double_counting(self):
        from apps.api.app.inventory_import import PendingResolvePreview,PendingResolveConfirm
        prior={"edition_key":"deluxe","entry_title":"Already linked",
               "edition_declared":"Deluxe","main_volumes":34,
               "duplicate_copies":0,"other_editions_unknown":1}
        db=DummyDb(existing=prior)
        router=self.endpoints(db)
        preview=router["/inventory/pending/resolve/preview"](
            PendingResolvePreview(source_key="Inventaire!A29",manga_id=15))
        self.assertTrue(preview["same_edition_exists"])
        self.assertEqual(preview["allowed_actions"],["MARK_DUPLICATE"])
        self.assertEqual(preview["existing_declarations"][0]["main_volumes"],34)
        confirm=router["/inventory/pending/resolve"]
        with self.assertRaises(HTTPException) as bad_mode:
            confirm(PendingResolveConfirm(source_key="Inventaire!A29",manga_id=15,
              confirmation_token=preview["confirmation_token"],
              acknowledge_work_and_edition=True))
        self.assertEqual(bad_mode.exception.status_code,409)
        with self.assertRaises(HTTPException) as missing_ack:
            confirm(PendingResolveConfirm(source_key="Inventaire!A29",manga_id=15,
              confirmation_token=preview["confirmation_token"],
              acknowledge_work_and_edition=True,resolution_mode="MARK_DUPLICATE"))
        self.assertEqual(missing_ack.exception.status_code,422)
        confirmed=confirm(PendingResolveConfirm(source_key="Inventaire!A29",manga_id=15,
              confirmation_token=preview["confirmation_token"],
              acknowledge_work_and_edition=True,resolution_mode="MARK_DUPLICATE",
              acknowledge_existing_inventory=True))
        self.assertEqual(confirmed["resolution_mode"],"MARK_DUPLICATE")
        self.assertFalse(confirmed["new_declaration_created"])
        self.assertTrue(any("INSERT INTO user_manga_inventory_resolution" in q
                            for q,_ in db.queries))
        self.assertFalse(any("INSERT INTO user_manga_inventory_declaration" in q
                             for q,_ in db.queries))
        audit=next(p for q,p in db.queries
                   if "INSERT INTO user_manga_inventory_resolution" in q)
        self.assertEqual(audit["mode"],"MARK_DUPLICATE")
        self.assertTrue(any("DELETE FROM user_manga_inventory_pending" in q
                            for q,_ in db.queries))

    def test_not_interested_conflict_keeps_pending_untouched(self):
        from apps.api.app.inventory_import import PendingResolvePreview
        db=DummyDb(rejected={"library_status":"NOT_INTERESTED"})
        endpoint=self.endpoints(db)["/inventory/pending/resolve/preview"]
        with self.assertRaises(HTTPException) as caught:
            endpoint(PendingResolvePreview(source_key="Inventaire!A29",manga_id=15))
        self.assertEqual(caught.exception.status_code,409)
        self.assertFalse(any("INSERT INTO" in q for q,_ in db.queries))

    def test_pending_missing_and_missing_manga_stay_unchanged(self):
        from apps.api.app.inventory_import import PendingResolvePreview
        for case in ("pending","manga"):
            db=DummyDb()
            setattr(db,case,None)
            endpoint=self.endpoints(db)["/inventory/pending/resolve/preview"]
            with self.assertRaises(HTTPException) as caught:
                endpoint(PendingResolvePreview(source_key="Inventaire!A29",manga_id=15))
            self.assertEqual(caught.exception.status_code,404)
            self.assertEqual(db.commits,0)


if __name__=="__main__":
    unittest.main()
