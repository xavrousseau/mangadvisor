"""Offline staging tests: only isolated SQL writes, no remote API or ownership changes."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipelines.engine.scripts import prepare_bibliographic_staging as st


def candidate(id="5383", title="Wind Breaker", evidence="EXACT_TITLE"):
    return {"id": id, "title": title, "evidence": evidence,
            "format": "manga", "aliases": []}


def details(*, lang="fr", medium="print", isbn="9782811669058",
            edition="standard"):
    return {"status": "OK", "id": "5383", "title": "Wind Breaker",
            "authors": ["Satoru Nii"], "publishers": ["Pika Édition"],
            "genres": ["Action"], "themes": ["École"], "aliases": ["ウィンドブレイカー"],
            "editions": [{"lang": lang, "medium": medium, "edition": edition,
                          "volume_count": 26}],
            "book_references": [{"isbn13": isbn, "lang": lang, "medium": medium,
                                 "edition_label": edition, "volume_label": "1",
                                 "released_on": "2023-02-15"}],
            "volume_items_seen": 26, "book_references_truncated": True}


def fixture():
    a = candidate()
    b = candidate("27705")
    return {
        "format_version": 2, "sample_count": 2,
        "generated_at": "2026-10-21T10:44:19Z",
        "providers": {"scrinis": {}, "mangaupdates": {}},
        "entries": [
            {"title": "Wind Breaker", "origin": "pending", "market_target": "FR_PRINT",
             "sources": {"scrinis": {
                "status": "AMBIGUOUS", "candidates": [a, b],
                "competing_details": [
                    {"id": "5383", "status": "OK", "details": details()},
                    {"id": "27705", "status": "OK", "details": details(
                        isbn="9782494300286")}],
                "matching_review": {
                    "edition_targets": [],
                    "competing_evidence": [
                        {"id": "5383", "work": {"score": 60},
                         "edition": {"score": 65}},
                        {"id": "27705", "work": {"score": 60},
                         "edition": {"score": 65}}]}}},
            },
            {"title": "Dragon Ball", "origin": "owned", "market_target": "FR_PRINT",
             "sources": {"mangaupdates": {
                 "status": "EXACT_TITLE",
                 "selected_id": "999",
                 "candidates": [{"id": "999", "title": "Dragon Ball",
                                 "evidence": "EXACT_TITLE", "format": "Manga"}],
                 "matching_review": {"edition_targets": ["Pastel", "Deluxe"],
                                     "work": {"score": 60},
                                     "edition": {"score": 0}},
                 "detail_status": "NOT_REQUESTED"
             }}}
        ],
    }


class FakeCursor:
    def __init__(self, database):
        self.db = database
        self.last = ""
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params=None):
        upper = sql.strip().upper()
        # CREATE and INSERT only for bib_stage_*; all other tables read only.
        if upper.startswith("INSERT"):
            self.db.inserts.append((sql, params))
            self.db.ident += 1
        elif upper.startswith("CREATE"):
            assert "BIB_STAGE_" in upper
            assert "MANGA_ID" not in upper
        else:
            assert upper.startswith("SELECT")
        self.last = upper
        self.db.calls.append((sql, params))
    def fetchone(self):
        if self.last.startswith("INSERT INTO BIB_STAGE_CANDIDATE"):
            return {"id": self.db.ident}
        if "FROM BIB_STAGE_BATCH" in self.last:
            return {"source_sha256": "abc"} if self.db.already else None
        if "TO_REGCLASS" in self.last:
            return {"tbl": "bnf_bulk_notice" if self.db.has_bnf else None}
        if "FROM BNF_BULK_NOTICE" in self.last:
            return {"n": 2}
        raise AssertionError(self.last)


class FakeDB:
    def __init__(self, *, already=False, has_bnf=False):
        self.calls, self.inserts, self.ident = [], [], 0
        self.already = already
        self.has_bnf = has_bnf
        self.transaction_count = 0
    def cursor(self): return FakeCursor(self)
    def transaction(self):
        db = self
        class Txn:
            def __enter__(self): db.transaction_count += 1
            def __exit__(self, *_): return False
        return Txn()


class BibliographicStagingTests(unittest.TestCase):
    def test_converts_distinct_works_and_never_uses_other_source_isbn(self):
        result = st.convert_report(fixture(), "a" * 64)
        self.assertEqual(result["entries"], 2)
        self.assertEqual(len(result["works"]), 3)
        self.assertEqual(len(result["editions"]), 2)
        self.assertEqual(len(result["volumes"]), 2)
        self.assertEqual({x["external_id"] for x in result["works"]},
                         {"5383", "27705", "999"})
        self.assertEqual({x["title"] for x in result["works"]},
                         {"Wind Breaker", "Dragon Ball"})
        self.assertEqual({v[1] for v in result["volumes"]},
                         {"9782811669058", "9782494300286"})
        self.assertEqual(next(w for w in result["works"] if w["external_id"] == "999")
                         ["edition_declarations"], ["Pastel", "Deluxe"])
        self.assertTrue(all(w["reference_truncated"] for w in result["works"]
                            if w["provider"] == "scrinis"))
        self.assertEqual(st.preview_summary(result)["decision"], "REVIEW_REQUIRED")

    def test_edition_family_and_tome_collisions_are_visible_but_not_linked(self):
        stage = st.convert_report(fixture(), "a"*64)
        key = (1, "scrinis", "5383")
        code = "9782811669058"
        # One ISBN reused as Deluxe and Pastel must not become a confirmed edition.
        stage["volumes"].append((key, code, "fr", "print", "deluxe", "1", ""))
        stage["volumes"].append((key, code, "fr", "print", "pastel", "1", ""))
        report = st.preview_summary(stage)
        self.assertEqual(report["isbn_conflict_count"], 1)
        self.assertEqual(report["isbn_conflicts_sample"][0]["reason"],
                         "CONFLICTING_EDITION_FAMILIES")
        self.assertFalse(report["isbn_conflicts_sample"][0]["registration_ready"])
        self.assertEqual(report["ownership_mutations"], 0)

    def test_conflicting_tome_or_competing_works_are_not_silent(self):
        stage = st.convert_report(fixture(), "b"*64)
        code = "9782811669058"
        source = (1, "scrinis", "5383")
        stage["volumes"].append((source, code, "fr", "print", "standard", "Tome 2", ""))
        report = st.preview_summary(stage)
        self.assertEqual(report["isbn_conflicts_sample"][0]["reason"],
                         "CONFLICTING_TOME_NUMBERS")
        # An ISBN assigned to different input works is suspicious even when
        # provider edition strings agree.
        stage["volumes"].append(((2, "mangaupdates", "999"), code,
                                 "fr", "print", "standard", "1", ""))
        report = st.preview_summary(stage)
        self.assertEqual(report["isbn_conflicts_sample"][0]["reason"],
                         "COMPETING_INPUT_WORKS")

    def test_no_bare_publication_year_invented_as_tome(self):
        self.assertIsNone(st._volume_number("2024"))
        self.assertEqual(st._volume_number("03"), 3)
        self.assertEqual(st._volume_number("Tome 12"), 12)
        self.assertIsNone(st._volume_number("3D2Y"))

    def test_rejects_invalid_origin_or_market_override(self):
        doc = fixture()
        doc["entries"][0]["market_target"] = "INTERNATIONAL"
        with self.assertRaisesRegex(ValueError, "incohérente"):
            st.convert_report(doc, "b"*64)
        doc["entries"][0]["market_target"] = "FR_PRINT"
        doc["entries"][0]["origin"] = "unknown"
        with self.assertRaisesRegex(ValueError, "inconnu"):
            st.convert_report(doc, "b"*64)

    def test_rejects_invalid_isbn_and_ebook_for_french_paper_counts(self):
        doc = fixture()
        data = doc["entries"][0]["sources"]["scrinis"]["competing_details"][0]["details"]
        data["book_references"].append({"isbn13": "9782811669059", "lang": "fr",
                                        "medium": "print", "edition_label": "standard"})
        data["book_references"].append({"isbn13": "9780306406157", "lang": "fr",
                                        "medium": "ebook", "edition_label": "standard"})
        stage = st.convert_report(doc, "c"*64)
        self.assertEqual(len(stage["volumes"]), 3)
        self.assertEqual(st.preview_summary(stage)["french_print_isbn_evidence"], 2)

    def test_unknown_or_unread_candidate_never_inherits_detail(self):
        doc = fixture()
        doc["entries"][0]["sources"]["scrinis"]["candidates"].append(
            candidate("300", "Wind Breaker X", "SUGGESTION_ONLY"))
        stage = st.convert_report(doc, "d"*64)
        third = next(w for w in stage["works"] if w["external_id"] == "300")
        self.assertEqual(third["detail_status"], "NOT_AVAILABLE")
        self.assertEqual(third["authors"], [])
        self.assertEqual(third["edition_score"], None)
        self.assertNotIn(((1, "scrinis", "300"), "fr", "print", "standard", 26),
                         stage["editions"])

    def test_commit_only_to_isolated_tables_and_replay_safe(self):
        stage = st.convert_report(fixture(), "e"*64)
        db = FakeDB()
        response = st.import_stage(db, stage, report_file="comparatif_sources_v2_20261021_104419_954922.json")
        self.assertEqual(response["status"], "PREPARED_FOR_REVIEW")
        self.assertEqual(db.transaction_count, 1)
        self.assertEqual(len(db.inserts), 1 + 3 + 2 + 2)
        self.assertTrue(all("bib_stage_" in statement.lower() for statement, _ in db.inserts))
        self.assertTrue(all("user_manga" not in statement.lower() for statement, _ in db.inserts))
        # A second import of identical report must not create ANY candidate/volume.
        db2 = FakeDB(already=True)
        response = st.import_stage(db2, stage, report_file="same.json")
        self.assertEqual(response["status"], "ALREADY_PREPARED")
        self.assertEqual(db2.inserts, [])

    def test_optional_bnf_crosscheck_is_read_only(self):
        stage = st.convert_report(fixture(), "f"*64)
        db = FakeDB(has_bnf=True)
        result = st.bnf_crosscheck(db, stage)
        self.assertEqual(result["status"], "ISBN_BIBLIOGRAPHIC_CROSSCHECK_ONLY")
        self.assertEqual(result["matches"], 2)
        self.assertFalse(result["ownership_verified"])
        self.assertEqual(len(db.inserts), 0)
        db2 = FakeDB(has_bnf=False)
        self.assertEqual(st.bnf_crosscheck(db2, stage)["status"],
                         "BNF_BULK_STAGING_NOT_LOADED")

    def test_latest_report_selected_locally_and_safe_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "comparatif_sources_v2_20261020_010101_000001.json").write_text("{}")
            latest = base / "comparatif_sources_v2_20261021_104419_954922.json"
            latest.write_text(json.dumps(fixture()))
            self.assertEqual(st.select_report(None, base), latest)
            with self.assertRaises(ValueError):
                st.select_report("../private.json", base)
            with self.assertRaises(ValueError):
                st.select_report("other.json", base)
            sha, report = st.read_report(latest)
            self.assertEqual(len(sha), 64)
            self.assertEqual(report["sample_count"], 2)

    def test_preview_has_no_database_access_or_canonical_write(self):
        stage = st.convert_report(fixture(), "f"*64)
        with tempfile.TemporaryDirectory() as tmp:
            js, cs = st.save_preview(stage, Path(tmp))
            report = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(report["ownership_mutations"], 0)
            self.assertEqual(report["canonical_mutations"], 0)
            rows = cs.read_text(encoding="utf-8-sig")
            self.assertIn("REVIEW_REQUIRED", rows)
            self.assertIn("Dragon Ball", rows)
            self.assertIn("Wind Breaker", rows)


if __name__ == "__main__":
    unittest.main()
