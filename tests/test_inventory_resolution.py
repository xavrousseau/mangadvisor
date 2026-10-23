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
        if "FROM user_manga_inventory_declaration" in self.last_sql:
            return ([self.db.existing] if isinstance(self.db.existing,dict)
                    else list(self.db.existing or []))
        return self.db.candidates if "FROM manga m" in self.last_sql else []


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

    def test_existing_edition_requires_archive_and_consent(self):
        from apps.api.app.inventory_import import PendingResolvePreview, PendingResolveConfirm
        old={"edition_key":"deluxe", "entry_title":"Dragon Ball Deluxe",
             "edition_declared":"Deluxe", "main_volumes":34,
             "duplicate_copies":0, "other_editions_unknown":0}
        db=DummyDb(existing=old)
        endpoints=self.endpoints(db)
        preview=endpoints["/inventory/pending/resolve/preview"](
            PendingResolvePreview(source_key="Inventaire!A29",manga_id=15)
        )
        self.assertTrue(preview["same_edition_exists"])
        self.assertEqual(preview["allowed_actions"],["MARK_DUPLICATE"])
        self.assertEqual(preview["existing_declarations"][0]["main_volumes"],34)
        endpoint=endpoints["/inventory/pending/resolve"]
        args=dict(source_key="Inventaire!A29",manga_id=15,
                  confirmation_token=preview["confirmation_token"],
                  acknowledge_work_and_edition=True)
        for params in [dict(resolution_mode="CREATE_DECLARATION",acknowledge_existing_inventory=True),
                       dict(resolution_mode="MARK_DUPLICATE",acknowledge_existing_inventory=False)]:
            with self.subTest(params=params), self.assertRaises(HTTPException):
                endpoint(PendingResolveConfirm(**args,**params))
        self.assertFalse(any("INSERT INTO" in q for q,_ in db.queries))
        result=endpoint(PendingResolveConfirm(
            **args,resolution_mode="MARK_DUPLICATE",
            acknowledge_existing_inventory=True))
        self.assertEqual(result["resolution_mode"],"MARK_DUPLICATE")
        self.assertFalse(result["new_declaration_created"])
        self.assertEqual(db.commits,1)
        sqls=[q for q,_ in db.queries]
        self.assertFalse(any("INSERT INTO user_manga_inventory_declaration" in q for q in sqls))
        self.assertTrue(any("INSERT INTO user_manga_inventory_resolution" in q for q in sqls))
        audit=next(p for q,p in db.queries if "INSERT INTO user_manga_inventory_resolution" in q)
        self.assertEqual(audit["mode"],"MARK_DUPLICATE")
        self.assertTrue(any("DELETE FROM user_manga_inventory_pending" in q for q in sqls))

    def test_other_edition_requires_explicit_review_before_adding(self):
        from apps.api.app.inventory_import import PendingResolvePreview, PendingResolveConfirm
        existing={"edition_key":"pastel", "entry_title":"Dragon Ball Pastel",
                  "edition_declared":"Pastel", "main_volumes":42,
                  "duplicate_copies":0, "other_editions_unknown":0}
        db=DummyDb(existing=existing)
        endpoints=self.endpoints(db)
        preview=endpoints["/inventory/pending/resolve/preview"](
            PendingResolvePreview(source_key="Inventaire!A29",manga_id=15)
        )
        self.assertEqual(preview["allowed_actions"],["CREATE_DECLARATION","MARK_DUPLICATE"])
        self.assertFalse(preview["same_edition_exists"])
        result=endpoints["/inventory/pending/resolve"](PendingResolveConfirm(
            source_key="Inventaire!A29",manga_id=15,
            confirmation_token=preview["confirmation_token"],
            acknowledge_work_and_edition=True,
            acknowledge_existing_inventory=True,
            resolution_mode="CREATE_DECLARATION"
        ))
        self.assertTrue(result["new_declaration_created"])
        declaration=next(p for q,p in db.queries if "INSERT INTO user_manga_inventory_declaration" in q)
        self.assertEqual(declaration["edition_key"],"deluxe")


    def test_read_only_bulk_triage_distinguishes_work_and_edition_risks(self):
        from apps.api.app.inventory_resolution import triage_pending_rows
        rows = [
            {**PENDING, "source_key": "A", "work_declared": "Dragon Ball",
             "edition_declared": "Deluxe", "candidate_ids": [15, 99]},
            {**PENDING, "source_key": "B", "entry_title": "Berserk",
             "work_declared": "Berserk", "edition_declared": "Prestige",
             "candidate_ids": []},
            {**PENDING, "source_key": "C", "entry_title": "Bleach",
             "work_declared": "Bleach", "edition_declared": "Classic",
             "candidate_ids": []},
            {**PENDING, "source_key": "D", "entry_title": "Title missing",
             "work_declared": "Title missing", "candidate_ids": []},
            {**PENDING, "source_key": "E", "entry_title": "Unknown alias",
             "work_declared": "Unknown alias", "candidate_ids": [80]},
        ]
        catalog = [
            {**MANGA, "exact_aliases": []},
            {"id": 99, "title": "Dragon Ball GT", "title_english": None,
             "title_japanese": None, "source_mal_id": 99,
             "manga_type": "Manga", "volumes": 3, "exact_aliases": []},
            {"id": 25, "title": "Berserk", "title_english": None,
             "title_japanese": None, "source_mal_id": 25,
             "manga_type": "Manga", "volumes": 42, "exact_aliases": []},
            {"id": 36, "title": "Bleach", "title_english": None,
             "title_japanese": None, "source_mal_id": 36,
             "manga_type": "Manga", "volumes": 74, "exact_aliases": []},
            {"id": 37, "title": "Another Bleach", "title_english": None,
             "title_japanese": None, "source_mal_id": 37,
             "manga_type": "Manga", "volumes": None, "exact_aliases": ["bleach"]},
            {"id": 80, "title": "Another title", "title_english": None,
             "title_japanese": None, "source_mal_id": 80,
             "manga_type": "Manga", "volumes": None, "exact_aliases": []},
        ]
        result = triage_pending_rows(
            rows, catalog, [{"manga_id": 15, "edition_key": "deluxe"},
                            {"manga_id": 25, "edition_key": "classic"}], {36},
        )
        indexed = {r["source_key"]: r for r in result["items"]}
        self.assertEqual(indexed["A"]["review_category"], "CONFLICTING_SUGGESTIONS")
        self.assertTrue(indexed["A"]["candidates"][0]["same_edition_already_declared"])
        self.assertEqual(indexed["B"]["review_category"], "SINGLE_EXACT_SUGGESTION")
        self.assertTrue(indexed["B"]["candidates"][0]["has_existing_declaration"])
        self.assertFalse(indexed["B"]["candidates"][0]["same_edition_already_declared"])
        self.assertEqual(indexed["C"]["review_category"], "AMBIGUOUS_EXACT")
        self.assertTrue(indexed["C"]["candidates"][0]["library_not_interested"])
        self.assertEqual(indexed["D"]["review_category"], "SEARCH_REQUIRED")
        self.assertEqual(indexed["E"]["review_category"], "SAVED_SUGGESTIONS_ONLY")
        self.assertEqual(result["count"], 5)
        self.assertEqual(result["confirmed_editions_written"], 0)
        self.assertEqual(result["inventory_mutations"], 0)
        self.assertTrue(all(r["manual_confirmation_required"] and
                            not r["automatic_association"] for r in result["items"]))
        self.assertTrue(all(not c["isbn_verified"] for r in result["items"]
                            for c in r["candidates"]))

    def test_pending_triage_endpoint_reads_only_current_user_and_no_supplier(self):
        from apps.api.app.inventory_resolution import TRIAGE_PENDING_SQL, TRIAGE_CATALOG_SQL

        class TriageCursor:
            def __init__(self, db): self.db = db
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, params=None):
                if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
                    raise AssertionError("Triage must remain SQL read-only")
                self.db.calls.append((sql, params))
                self.sql = sql
            def fetchall(self):
                if self.sql == TRIAGE_PENDING_SQL:
                    return [{**PENDING, "candidate_ids": [15]}]
                if self.sql == TRIAGE_CATALOG_SQL:
                    return [{**MANGA, "exact_aliases": []}]
                if "FROM user_manga_inventory_declaration" in self.sql:
                    return []
                if "FROM user_manga_library" in self.sql:
                    return []
                if "FROM manga_bnf_candidate" in self.sql or "FROM manga_fr_edition" in self.sql:
                    return []
                raise AssertionError(self.sql)

        class TriageDB:
            def __init__(self): self.calls = []; self.commits = 0
            def __call__(self): return self
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def cursor(self): return TriageCursor(self)
            def commit(self): self.commits += 1

        db = TriageDB()
        fn = self.endpoints(db)["/inventory/pending/triage"]
        output = fn()
        self.assertEqual(output["review_categories"], {"SINGLE_EXACT_SUGGESTION": 1})
        self.assertEqual(output["count"], 1)
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.calls[0][1], {"user_id": 1})
        self.assertEqual(db.calls[1][1],
                         {"terms": ["dragon ball"], "saved_ids": [15]})
        self.assertTrue(all(
            ("user_id" in params or "manga_ids" in params)
            for _, params in db.calls[2:]
        ))
        self.assertTrue(all(not sql.lstrip().upper().startswith(
            ("UPDATE", "INSERT", "DELETE")) for sql, _ in db.calls))

    def test_triage_incomplete_catalog_disables_single_exact_claim(self):
        from apps.api.app.inventory_resolution import triage_pending_rows, _triage_term
        self.assertEqual(_triage_term({
            "entry_title": "Dragon Ball (34 tomes)", "work_declared": None
        }), "dragon ball (34 tomes)")
        result = triage_pending_rows(
            [PENDING], [{**MANGA, "exact_aliases": []}], [], set(),
            lookup_limited=True,
        )
        self.assertEqual(result["review_categories"], {"INCOMPLETE_LOOKUP": 1})
        self.assertTrue(result["lookup_limited"])
        self.assertFalse(result["automatic_association"])


    def test_discover_pending_is_read_only_and_external_bnf_is_opt_in(self):
        from apps.api.app.inventory_resolution import DISCOVERY_SQL
        from unittest.mock import patch
        class Cursor:
            def __init__(self, db): self.db=db; self.sql=""
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, params=None):
                assert sql.lstrip().upper().startswith("SELECT")
                self.sql=sql; self.db.calls.append((sql, params))
            def fetchone(self): return {**PENDING, "entry_title": "Adieu Eri",
                                         "work_declared": None}
            def fetchall(self):
                if self.sql == DISCOVERY_SQL:
                    return [{**MANGA, "title": "Sayonara Eri", "id": 88}]
                return []
        class Db:
            def __init__(self): self.calls=[]
            def __call__(self): return self
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def cursor(self): return Cursor(self)
            def commit(self): raise AssertionError("Forbidden write")
        db=Db()
        endpoint=self.endpoints(db)["/inventory/pending/discover"]
        with patch("apps.api.app.inventory_resolution.search_bnf_by_title") as bnf:
            output=endpoint(source_key="Inventaire!A29",include_bnf=False)
            bnf.assert_not_called()
        self.assertEqual(output["query"], "Adieu Eri")
        self.assertIn("eri",output["search_tokens"])
        self.assertEqual(output["catalog_candidates"][0]["title"],"Sayonara Eri")
        self.assertFalse(output["automatic_association"])
        self.assertFalse(output["writes_performed"])
        with patch("apps.api.app.inventory_resolution.search_bnf_by_title",
                   return_value={"items":[{"isbn13":"9782871294146",
                                            "status":"CANDIDATE_UNCONFIRMED"}]}) as bnf:
            output=endpoint(source_key="Inventaire!A29",include_bnf=True)
            bnf.assert_called_once_with("Adieu Eri")
            self.assertEqual(output["bnf"]["status"],"BOOK_NOTICES_UNVERIFIED")
            self.assertFalse(output["isbn_ownership_verified"])
        self.assertTrue(all(not x.lstrip().upper().startswith(
            ("INSERT", "UPDATE", "DELETE")) for x, _ in db.calls))


    def test_international_crosswalk_is_opt_in_and_flags_conflicting_ids(self):
        from unittest.mock import patch
        db=DummyDb()
        endpoint=self.endpoints(db)["/inventory/pending/discover"]
        with patch("apps.api.app.inventory_resolution.search_anilist") as anilist, \
             patch("apps.api.app.inventory_resolution.search_kitsu_by_mal") as kitsu:
            result=endpoint(source_key=PENDING["source_key"])
            anilist.assert_not_called()
            kitsu.assert_not_called()
            self.assertEqual(result["anilist"]["status"],"NOT_REQUESTED")
            self.assertEqual(result["kitsu"]["status"],"NOT_REQUESTED")
            self.assertFalse(result["external_lookup_requested"])
        ani={"status":"CROSS_ID_CANDIDATES","items":[{
            "source_mal_id":42,"anilist_id":801,
            "titles":[{"language":"romaji","title":"Dragon Ball"}],
            "identity_confirmed":False
        }]}
        k={"status":"MAL_ANILIST_CROSS_ID_REVIEW","items":[{
            "status":"MAL_ANILIST_CROSS_ID_REVIEW",
            "source_mal_id":42,"anilist_ids":[801],
            "kitsu_id":998,"identity_confirmed":False
        }]}
        with patch("apps.api.app.inventory_resolution.search_anilist",
                   return_value=ani) as anilist, \
             patch("apps.api.app.inventory_resolution.search_kitsu_by_mal",
                   return_value=k) as kitsu:
            result=endpoint(source_key=PENDING["source_key"],
                            include_anilist=True,include_kitsu=True)
            anilist.assert_called_once_with("Dragon Ball")
            kitsu.assert_called_once_with(42)
        self.assertEqual(result["international_id_evidence"]["status"],
                         "CROSS_ID_AGREEMENT_REVIEW")
        self.assertFalse(result["international_id_evidence"]
                         ["independent_identity_proven"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["automatic_association"])
        self.assertEqual(db.commits,0)
        with patch("apps.api.app.inventory_resolution.search_anilist",
                   return_value=ani), \
             patch("apps.api.app.inventory_resolution.search_kitsu_by_mal",
                   return_value={**k, "items":[{**k["items"][0],
                         "anilist_ids":[999]}]}):
            conflict=endpoint(source_key=PENDING["source_key"],
                              include_anilist=True,include_kitsu=True)
        self.assertEqual(conflict["international_id_evidence"]["status"],
                         "CONTRADICTION_REVIEW")
        self.assertFalse(conflict["automatic_association"])

    def test_rejected_library_status_is_never_resolved(self):
        from apps.api.app.inventory_import import PendingResolvePreview
        db=DummyDb(rejected={"library_status":"NOT_INTERESTED"})
        with self.assertRaises(HTTPException) as caught:
            self.endpoints(db)["/inventory/pending/resolve/preview"](
                PendingResolvePreview(source_key="Inventaire!A29",manga_id=15))
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
