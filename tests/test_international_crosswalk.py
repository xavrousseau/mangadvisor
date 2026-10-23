"""No-network checks of manga-only AniList/Kitsu cross-ID discovery."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from apps.api.app.international_crosswalk import (
    ANILIST_QUERY,parse_anilist,search_anilist,_kitsu_item_ids,
    _parse_kitsu_mapping,search_kitsu_by_mal,combine_cross_id_sources,
)

def anilist_item(aid=15800,mal=145863,name="Sayonara Eri"):
    return {"id":aid,"idMal":mal,"type":"MANGA","format":"ONE_SHOT",
            "title":{"romaji":name,"english":"Goodbye, Eri",
                     "native":"さよなら絵梨"},
            "synonyms":["Adieu Eri"]}

def kitsu_mapping(site,external,item_id="4567"):
    return {"type":"mappings",
            "attributes":{"externalSite":site,"externalId":str(external)},
            "relationships":{"item":{"data":{"type":"manga","id":item_id}}}}

class InternationalCrosswalkTests(unittest.TestCase):
    def test_anilist_filters_anime_and_preserves_strong_ids_with_aliases(self):
        self.assertIn("type: MANGA",ANILIST_QUERY)
        data={"data":{"Page":{"media":[
            anilist_item(),
            {"id":2,"idMal":145863,"type":"ANIME","format":"TV",
             "title":{"english":"Not manga"}},
            anilist_item(),
        ]}}}
        found=parse_anilist(data)
        self.assertEqual(len(found["items"]),1)
        item=found["items"][0]
        self.assertEqual(item["source_mal_id"],145863)
        self.assertEqual(item["titles"][3]["title"],"Adieu Eri")
        self.assertFalse(item["identity_confirmed"])

    def test_anilist_graphql_errors_are_unavailable_not_no_match(self):
        with self.assertRaises(ValueError):
            parse_anilist({"errors":[{"message":"rate limited"}],"data":None})
        with patch("apps.api.app.international_crosswalk._read_json",
                   return_value={"errors":[{"message":"rate limited"}]}):
            with self.assertRaises(HTTPException) as ex:
                search_anilist("Adieu Eri")
        self.assertEqual(ex.exception.status_code,503)

    def test_kitsu_mapping_stays_manga_scoped_and_checks_expected_mal(self):
        page={"data":[
            kitsu_mapping("myanimelist/manga","145863"),
            kitsu_mapping("myanimelist/anime","145863",item_id="99"),
            {**kitsu_mapping("myanimelist/manga","145863",item_id="21"),
             "relationships":{"item":{"data":{"type":"anime","id":"21"}}}},
        ]}
        self.assertEqual(_kitsu_item_ids(page,145863),[4567])
        evidence=_parse_kitsu_mapping({"data":[
            kitsu_mapping("myanimelist/manga","145863"),
            kitsu_mapping("anilist/manga","15800"),
        ]},145863,4567)
        self.assertEqual(evidence["status"],"MAL_ANILIST_CROSS_ID_REVIEW")
        self.assertEqual(evidence["anilist_ids"],[15800])
        self.assertFalse(evidence["identity_confirmed"])

    def test_conflicting_kitsu_mappings_fail_closed(self):
        record={"data":[
            kitsu_mapping("myanimelist/manga","145863"),
            kitsu_mapping("myanimelist/manga","444"),
            kitsu_mapping("anilist/manga","15800"),
        ]}
        inconsistent=_parse_kitsu_mapping(record,145863,4567)
        self.assertEqual(inconsistent["status"],"MAL_ID_CONFLICT_OR_MISSING")
        anilist={"items":[{"source_mal_id":145863,"anilist_id":15800}]}
        merged=combine_cross_id_sources(anilist,[{"items":[inconsistent]}])
        self.assertEqual(merged["status"],"CONTRADICTION_REVIEW")
        self.assertFalse(merged["independent_identity_proven"])

    def test_crosswalk_agreement_is_not_independent_proof(self):
        linked={"status":"MAL_ANILIST_CROSS_ID_REVIEW",
                "source_mal_id":145863,"anilist_ids":[15800],"kitsu_id":4567}
        ani={"items":[{"source_mal_id":145863,"anilist_id":15800}]}
        agreed=combine_cross_id_sources(ani,[{"items":[linked]}])
        self.assertEqual(agreed["status"],"CROSS_ID_AGREEMENT_REVIEW")
        self.assertFalse(agreed["independent_identity_proven"])
        bad=combine_cross_id_sources(
            ani,[{"items":[{**linked,"anilist_ids":[19999]}]}]
        )
        self.assertEqual(bad["status"],"CONTRADICTION_REVIEW")

    def test_kitsu_provider_down_never_means_mal_not_found(self):
        with patch("apps.api.app.international_crosswalk._read_json",
                   side_effect=HTTPException(status_code=503)):
            with self.assertRaises(HTTPException):
                search_kitsu_by_mal(145863)

    def test_duplicate_kitsu_items_are_ambiguous(self):
        with patch("apps.api.app.international_crosswalk._read_json",
                   return_value={"data":[
                       kitsu_mapping("myanimelist/manga",145863,item_id="42"),
                       kitsu_mapping("myanimelist/manga",145863,item_id="43"),
                   ]}):
            result=search_kitsu_by_mal(145863)
        self.assertEqual(result["status"],"AMBIGUOUS_KITSU_ITEMS")
        self.assertEqual(len(result["items"]),2)


if __name__=="__main__":
    unittest.main()
