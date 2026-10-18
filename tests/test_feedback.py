"""Non-destructive checks for persistent recommendation feedback."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from apps.api.app.main import (
    RecommendationFeedbackRequest,
    record_recommendation_feedback,
)


class FakeCursor:
    def __init__(self, exists=True, changed=True):
        self.exists, self.changed = exists, changed
        self.calls = []
        self.current = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        self.current = sql

    def fetchone(self):
        if self.current.startswith("SELECT id FROM manga"):
            return {"id": 5} if self.exists else None
        return (
            {"manga_id": 5, "library_status": self.calls[-1][1]["new_status"]}
            if self.changed else None
        )


class FakeConn:
    def __init__(self, exists=True, changed=True):
        self.cur = FakeCursor(exists, changed)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


class FeedbackTests(unittest.TestCase):
    def test_actions_have_existing_library_statuses(self):
        mapping = {
            "INTERESTED": "WANT_TO_READ",
            "ALREADY_READ": "READ",
            "NOT_FOR_ME": "NOT_INTERESTED",
        }
        for action, status in mapping.items():
            with self.subTest(action=action):
                conn = FakeConn()
                with patch("apps.api.app.main.get_connection", return_value=conn):
                    response = record_recommendation_feedback(
                        RecommendationFeedbackRequest(manga_id=5, action=action)
                    )
                self.assertEqual(response["library_status"], status)
                self.assertEqual(conn.cur.calls[-1][1]["new_status"], status)
                self.assertEqual(conn.commits, 1)

    def test_update_does_not_touch_notes_ratings_or_progress(self):
        conn = FakeConn()
        with patch("apps.api.app.main.get_connection", return_value=conn):
            record_recommendation_feedback(
                RecommendationFeedbackRequest(manga_id=5, action="INTERESTED")
            )
        update_sql = conn.cur.calls[-1][0]
        self.assertIn("SET library_status = EXCLUDED.library_status", update_sql)
        for field in ("user_score", "owned_volumes", "read_volumes", "notes",
                      "started_at", "finished_at", "is_favorite"):
            self.assertNotIn(f"{field} =", update_sql)
        self.assertIn("WHERE user_manga_library.library_status IN", update_sql)

    def test_existing_reading_owned_cannot_be_replaced_by_quick_dislike(self):
        conn = FakeConn(changed=False)
        with patch("apps.api.app.main.get_connection", return_value=conn):
            with self.assertRaises(HTTPException) as caught:
                record_recommendation_feedback(
                    RecommendationFeedbackRequest(manga_id=5, action="NOT_FOR_ME")
                )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(conn.commits, 0)

    def test_unknown_manga_rejected_without_write(self):
        conn = FakeConn(exists=False)
        with patch("apps.api.app.main.get_connection", return_value=conn):
            with self.assertRaises(HTTPException) as caught:
                record_recommendation_feedback(
                    RecommendationFeedbackRequest(manga_id=5, action="ALREADY_READ")
                )
        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(len(conn.cur.calls), 1)
        self.assertEqual(conn.commits, 0)

    def test_invalid_payload_rejected(self):
        with self.assertRaises(ValidationError):
            RecommendationFeedbackRequest(manga_id=-5, action="INTERESTED")
        with self.assertRaises(ValidationError):
            RecommendationFeedbackRequest(manga_id=5, action="MAYBE")


if __name__ == "__main__":
    unittest.main()
