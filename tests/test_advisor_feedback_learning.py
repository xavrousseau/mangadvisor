"""Conservative library-feedback learning: deterministic, explainable, bounded."""
import unittest

from apps.api.app.advisor import AdvisorContext, score_candidates
from apps.api.app.advisor_feedback import (
    FEEDBACK_SQL, build_feedback_profile, empty_feedback,
    feedback_evidence, feedback_summary,
)


def manga(mid, genres, themes=None, score=8.0):
    return {
        "id": mid,"title":f"CI manga {mid}","genres":genres,
        "themes":themes or [],"score":score,"popularity":mid,
        "synopsis":"","french_record_count":0,
        "preferred_format_record_count":0,
    }


class FeedbackLearningTests(unittest.TestCase):
    def test_statuses_come_from_existing_library_and_never_write(self):
        self.assertIn("user_manga_library", FEEDBACK_SQL)
        self.assertIn("COUNT(DISTINCT manga_id)", FEEDBACK_SQL)
        self.assertIn("'NOT_INTERESTED'", FEEDBACK_SQL)
        self.assertIn("'WANT_TO_READ'", FEEDBACK_SQL)
        for keyword in ("INSERT ", "DELETE ", "UPDATE ", "ALTER ", "DROP "):
            self.assertNotIn(keyword, FEEDBACK_SQL.upper())

    def test_single_dislike_is_not_an_entire_genre_ban(self):
        profile=build_feedback_profile([
            {"status":"NOT_INTERESTED","kind":"genres","tag":"mystery","sources":1}
        ])
        evidence=feedback_evidence(manga(1,["Mystery"]),profile,{"genres":set(),"themes":set()})
        self.assertEqual(evidence["repeated_rejection_tags"],[])
        self.assertEqual(evidence["rejection_penalty"],0)
        results=score_candidates([manga(1,["Mystery"])],AdvisorContext(mood="MYSTERY"),
                                 {"genres":set(),"themes":set()},5,profile)
        self.assertEqual([r["id"] for r in results],[1])

    def test_repeated_dislikes_soften_rank_not_hard_exclude(self):
        profile=build_feedback_profile([
            {"status":"NOT_INTERESTED","kind":"themes","tag":"psychological","sources":2},
        ])
        preferences={"genres":set(),"themes":set()}
        a=manga(1,["Mystery"],["Psychological"],score=8.2)
        b=manga(2,["Mystery"],["Detective"],score=8.0)
        prior=score_candidates([a,b],AdvisorContext(mood="MYSTERY",
                                 recommendation_balance="CLOSE"),preferences,2)
        self.assertEqual(prior[0]["id"],1)  # both receive explicit mood evidence
        updated=score_candidates([a,b],AdvisorContext(mood="MYSTERY",
                                   recommendation_balance="CLOSE"),preferences,2,profile)
        self.assertEqual(updated[0]["id"],2)
        self.assertEqual({m["id"] for m in updated},{1,2})
        refused=next(row for row in updated if row["id"]==1)
        self.assertEqual(refused["feedback_evidence"]["repeated_rejection_tags"],
                         ["Psychological"])

    def test_strong_likes_or_interested_override_repeated_category_refusal(self):
        rows=[
            {"status":"NOT_INTERESTED","kind":"genres","tag":"fantasy","sources":3},
            {"status":"WANT_TO_READ","kind":"genres","tag":"fantasy","sources":1},
        ]
        profile=build_feedback_profile(rows)
        liked=feedback_evidence(manga(9,["Fantasy"]),profile,
                                {"genres":set(),"themes":set()})
        self.assertEqual(liked["rejection_penalty"],0)
        self.assertEqual(liked["interest_bonus"],3)
        positive=feedback_evidence(manga(9,["Fantasy"]),
                                   build_feedback_profile(rows[:1]),
                                   {"genres":{"fantasy"},"themes":set()})
        self.assertEqual(positive["rejection_penalty"],0)

    def test_interested_is_light_and_not_called_already_read(self):
        profile=build_feedback_profile([
            {"status":"WANT_TO_READ","kind":"genres","tag":"adventure","sources":1},
            {"status":"WANT_TO_READ","kind":"themes","tag":"survival","sources":4},
            {"status":"READ","kind":"genres","tag":"action","sources":999},
            {"status":"NOT_INTERESTED","kind":"genres","tag":"adventure","sources":0},
        ])
        context=AdvisorContext(mood="ACTION",recommendation_balance="CLOSE")
        prefs={"genres":set(),"themes":set()}
        old=score_candidates([manga(1,["Action","Adventure"]),
                              manga(2,["Action"])],context,prefs,2)
        new=score_candidates([manga(1,["Action","Adventure"]),
                              manga(2,["Action"])],context,prefs,2,profile)
        self.assertEqual(old[0]["id"],2)
        self.assertEqual(new[0]["id"],1)
        self.assertEqual(new[0]["feedback_evidence"]["interested_tags"],["Adventure"])
        self.assertEqual(profile["interested"]["genres"]["adventure"],1)
        summary=feedback_summary(profile)
        self.assertEqual(summary["interested_tag_count"],2)
        self.assertEqual(summary["repeated_rejection_tag_count"],0)

    def test_exclusion_is_never_removed_from_explicit_filters(self):
        profile=build_feedback_profile([
            {"status":"WANT_TO_READ","kind":"genres","tag":"horror","sources":10}
        ])
        result=score_candidates([
            manga(1,["Mystery","Horror"],score=9.5),
            manga(2,["Mystery"],score=8.0),
        ],AdvisorContext(mood="MYSTERY",avoid_horror=True),
        {"genres":set(),"themes":set()},3,profile)
        self.assertEqual([m["id"] for m in result],[2])

    def test_empty_feedback_is_noop(self):
        rows=[manga(1,["Mystery"]),manga(2,["Mystery","Action"])]
        ctx=AdvisorContext(mood="MYSTERY",recommendation_balance="CLOSE")
        prefs={"genres":set(),"themes":set()}
        old=score_candidates(rows,ctx,prefs,6)
        new=score_candidates(rows,ctx,prefs,6,empty_feedback())
        self.assertEqual([r["id"] for r in old],[r["id"] for r in new])
        self.assertEqual(new[0]["feedback_evidence"],
                         {"interested_tags":[],"repeated_rejection_tags":[]})


if __name__=="__main__":
    unittest.main()
