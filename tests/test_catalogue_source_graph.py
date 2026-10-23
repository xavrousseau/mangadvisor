"""Source graph contracts: do not confuse synonyms, titles, works or ISBNs."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.api.app.catalogue_source_graph import (
    SCHEMA, BASE_BACKFILL, IDENTITY_COLLISIONS_SQL, title_key,
    register_non_mal_work, stage_external_facts, ensure_schema,
)
from pipelines.engine.scripts.rebuild_catalogue_source_graph import (
    parse_mal_ids, enrich_selected,
)


class FakeCursor:
    def __init__(self, store):
        self.store=store
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql,params=None):
        self.store.append((sql,params))
    def fetchone(self):
        return {"id":321}


class FakeConnection:
    def __init__(self):
        self.calls=[]
    def cursor(self):return FakeCursor(self.calls)


class SourceGraphTests(unittest.TestCase):
    def test_independent_internal_work_does_not_require_mal_id(self):
        conn=FakeConnection()
        work=register_non_mal_work(
            conn,"Radiant",source="PUBLISHER",
            external_id="https://www.ankama-shop.com/fr/radiant"
        )
        self.assertEqual(work,321)
        text,params=conn.calls[0]
        self.assertIn("VALUES(NULL,%s,%s,%s)",text)
        self.assertEqual(params[2],"Radiant")
        with self.assertRaises(ValueError):
            register_non_mal_work(conn,"Other title",source="SYNONYM",external_id="unknown")

    def test_jikan_synonyms_remain_discovery_only_or_collision_review(self):
        self.assertIn("WHEN a.source_name='TENRAI_MAL' THEN 'DISCOVERY_ONLY'",
                      BASE_BACKFILL)
        self.assertIn("THEN 'COLLISION_REVIEW'",BASE_BACKFILL)
        self.assertIn("WHEN a.source_name='TENRAI_MAL' THEN 'UNVERIFIED_SYNONYM'",
                      BASE_BACKFILL)
        self.assertIn("catalogue_legacy_canonical_key_idx",SCHEMA)
        self.assertIn("catalogue_work_title_key_idx",SCHEMA)
        self.assertIn("lower(btrim(other.title))=lower(btrim(a.alias))",BASE_BACKFILL)
        self.assertNotIn("DELETE FROM manga_title_alias",BASE_BACKFILL)
        self.assertNotIn("DROP TABLE manga",BASE_BACKFILL)
        self.assertNotIn("user_manga",BASE_BACKFILL)

    def test_external_sources_use_exact_mal_work_id_not_fuzzy_titles(self):
        conn=FakeConnection()
        result=stage_external_facts(
            conn,145863,provider="ANILIST",
            source_id="15800",url="https://anilist.co/manga/15800",
            titles=[
                {"language":"english","title":"Goodbye, Eri"},
                {"language":"fr","title":"Adieu Eri"},
                {"language":"unspecified","title":"Unknown"}
            ],
            relations=[{"mal_id":999,"media_type":"MANGA",
                        "relation_type":"SIDE_STORY"}],
        )
        self.assertEqual(result["status"],"STAGED_SOURCE_CLAIMS")
        self.assertEqual(result["stored"],4)
        self.assertFalse(result["identities_merged"])
        queries=[sql for sql,_ in conn.calls]
        self.assertIn("WHERE origin_source='MAL' AND origin_id=%s",queries[0])
        self.assertTrue(any("catalogue_title_claim" in sql for sql in queries))
        self.assertTrue(any("catalogue_work_relation" in sql for sql in queries))
        title_params=[p for q,p in conn.calls if
                     "INSERT INTO catalogue_title_claim" in q]
        self.assertEqual([x["language_code"] for x in title_params],["en","fr"])
        self.assertIn("identity_status='COLLISION_REVIEW'",IDENTITY_COLLISIONS_SQL)

    def test_unlinked_synonyms_and_unauthenticated_sources_are_rejected(self):
        conn=FakeConnection()
        for provider in ("UNVERIFIED_JIKAN","UNKNOWN"):
            with self.assertRaises(ValueError):
                stage_external_facts(conn,145863,provider=provider,
                    source_id="3",url="https://example.org")
        with self.assertRaises(ValueError):
            stage_external_facts(conn,0,provider="ANILIST",
                source_id="8",url="https://example.org")
        self.assertEqual(parse_mal_ids("145863,598,598"),[145863,598])
        with self.assertRaises(ValueError):
            parse_mal_ids(",".join(str(i) for i in range(1,11)))

    def test_live_provider_enrichment_requires_opt_in(self):
        conn=FakeConnection()
        with patch(
            "pipelines.engine.scripts.rebuild_catalogue_source_graph.search_anilist_by_mal_ids"
        ) as provider:
            report=enrich_selected(conn,[145863],set())
            provider.assert_not_called()
        self.assertEqual(report["requests"],0)
        self.assertEqual(report["new_claim_operations"],0)
        self.assertFalse(any("user_manga" in q for q,_ in conn.calls))

    def test_id_collision_has_no_merge_even_if_claims_agree_by_title(self):
        self.assertIn("other.work_id<>ident.work_id",IDENTITY_COLLISIONS_SQL)
        self.assertIn("ident.identity_status <> 'REJECTED'",IDENTITY_COLLISIONS_SQL)
        self.assertIn("source_name TEXT NOT NULL",SCHEMA)
        self.assertIn("target_provider TEXT NOT NULL",SCHEMA)
        self.assertNotIn("UPDATE manga SET",BASE_BACKFILL)

    def test_title_key_is_stable_for_french_accent(self):
        self.assertEqual(title_key("L'Attaque  des Titans"),
                         "l'attaque des titans")


if __name__=="__main__":
    unittest.main()
