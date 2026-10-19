"""Deterministic, privacy-safe coverage tests for large owned libraries."""
import unittest

from apps.api.app.library_seed_selection import (
    MAX_LIBRARY_SEEDS, choose_representative_sources,
    evidence_summary, evidence_tier,
)


def owned(mid, weight=1.0):
    return {
        "id": mid, "title": f"Example {mid}", "library_status": "OWNED",
        "is_favorite": False, "user_score": None, "positive_weight": weight,
    }


class LibrarySeedSelectionTests(unittest.TestCase):
    def test_large_owned_collection_covers_distinct_real_attributes(self):
        # Simulate a large collection such as 103 inventory entries, without
        # committing any actual personal titles or ownership data.
        sources = [owned(i) for i in range(1, 104)]
        # The first 20 owned mangas happen to share one common tag.
        tags = {i: {"g:action"} for i in range(1, 104)}
        tags[40] = {"g:sports", "t:team sports"}
        tags[62] = {"g:mystery", "t:psychological"}
        tags[86] = {"g:fantasy", "t:mythology"}
        chosen, strategy = choose_representative_sources(sources, tags)
        self.assertEqual(strategy, "RECORDED_ATTRIBUTE_DIVERSITY")
        self.assertLessEqual(len(chosen), MAX_LIBRARY_SEEDS)
        self.assertEqual(len({s["id"] for s in chosen}), len(chosen))
        chosen_ids = {source["id"] for source in chosen}
        self.assertTrue({40, 62, 86}.issubset(chosen_ids))
        self.assertNotEqual(chosen_ids, set(range(1, 9)))
        self.assertEqual(evidence_summary(sources)["level"], "OWNERSHIP_ONLY")
        self.assertIn("pas de gouts confirmes", evidence_summary(sources)["warning"])

    def test_strong_favorites_keep_existing_behavior(self):
        sources = [owned(i) for i in range(1, 18)]
        for i in (1, 4, 7, 8, 9, 11):
            sources[i - 1].update(is_favorite=True, positive_weight=5)
        chosen, strategy = choose_representative_sources(
            sources, {17: {"t:unique"}}
        )
        self.assertEqual([s["id"] for s in chosen], [1, 4, 7, 8, 9])
        self.assertEqual(strategy, "EXPLICIT_FAVORITES_OR_HIGH_RATINGS")
        self.assertEqual(evidence_summary(sources)["level"], "RECORDED_TASTE")

    def test_two_favorites_are_protected_then_diversify(self):
        sources = [owned(i) for i in range(1, 13)]
        sources[0].update(is_favorite=True, positive_weight=5)
        sources[6].update(user_score=9.0, positive_weight=5)
        tags = {i: {"g:action"} for i in range(1, 13)}
        tags[11] = {"t:sports"}
        chosen, strategy = choose_representative_sources(sources, tags)
        ids = [row["id"] for row in chosen]
        self.assertEqual(ids[:2], [1, 7])
        self.assertIn(11, ids)
        self.assertEqual(strategy, "RECORDED_ATTRIBUTE_DIVERSITY")

    def test_reading_outweighs_pure_ownership(self):
        sources = [owned(i) for i in range(1, 14)]
        sources[10].update(library_status="READ", positive_weight=3)
        chosen, _ = choose_representative_sources(
            sources, {1: {"t:unusual"}, 2: {"t:rare"}, 11: {"g:action"}}
        )
        self.assertEqual(chosen[0]["id"], 11)
        self.assertEqual(evidence_tier(sources[10]), 2)

    def test_a_low_rated_read_book_is_not_treated_as_favorite(self):
        disliked = owned(42)
        disliked.update(library_status="READ", user_score=5.0, positive_weight=1)
        self.assertEqual(evidence_tier(disliked), 0)
        self.assertEqual(evidence_summary([disliked])["level"], "OWNERSHIP_ONLY")

    def test_tags_are_queried_in_recommendations_endpoint_only(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "apps/api/app/main.py").read_text("utf-8")
        profile = source.split('@app.get("/library/profile")', 1)[1].split(
            '@app.post("/recommendations/feedback")', 1
        )[0]
        recommendations = source.split('@app.post("/recommendations/library")', 1)[1].split(
            '@app.get("/recommendations/similar")', 1
        )[0]
        self.assertNotIn("seed_tag_rows", profile)
        self.assertIn('seed_tag_rows = cur.fetchall()', recommendations)
        self.assertIn('choose_representative_sources(', recommendations)

    def test_no_tags_fallback_stable_and_no_artificial_confidence(self):
        sources = [owned(i) for i in range(1, 22)]
        first, strategy = choose_representative_sources(sources, {})
        second, _ = choose_representative_sources(sources, {})
        self.assertEqual([x["id"] for x in first], list(range(1, 9)))
        self.assertEqual(first, second)
        self.assertEqual(strategy, "WEIGHTED_FALLBACK_NO_TAGS")
        self.assertIsNotNone(evidence_summary(sources)["warning"])

    def test_very_small_library_and_interest_only(self):
        sources = [owned(1), owned(2)]
        chosen, strategy = choose_representative_sources(sources, {})
        self.assertEqual(chosen, sources)
        self.assertEqual(strategy, "SMALL_LIBRARY")
        sources[1]["library_status"] = "WANT_TO_READ"
        self.assertEqual(evidence_summary(sources)["level"], "OWNERSHIP_AND_INTEREST_ONLY")


if __name__ == "__main__":
    unittest.main()
