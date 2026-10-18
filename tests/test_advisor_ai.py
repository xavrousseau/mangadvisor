"""Local AI is only a validated *intent parser*; catalog logic stays deterministic."""
import io
import json
import os
import unittest
from unittest.mock import patch

from apps.api.app.advisor import AdvisorContext
from apps.api.app.advisor_ai import (
    LocalAiUnavailable, PATCHABLE_FIELDS, ai_status, local_ai_enabled,
    parse_intent_response, interpret_with_ollama,
)


class FakeResponse:
    def __init__(self, body):
        self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self, *args):return self.body


class LocalAiTests(unittest.TestCase):
    def test_disabled_does_not_attempt_network(self):
        with patch.dict(os.environ,{"OLLAMA_ENABLED":"false"}):
            self.assertFalse(local_ai_enabled())
            self.assertEqual(ai_status()["mode"],"guided")
            with patch("urllib.request.urlopen") as request:
                with self.assertRaises(LocalAiUnavailable):
                    interpret_with_ollama("Un thriller",AdvisorContext())
                request.assert_not_called()

    def test_supported_filters_keep_prior_context_and_use_real_enums(self):
        old=AdvisorContext(mood="MYSTERY",length="SHORT",french="PREFER")
        result,changes,more=parse_intent_response(json.dumps({
            "updates":{"only_finished":True,"avoid_gore":True},
            "more":False,"reset":False,
        }),old)
        self.assertEqual(result.mood,"MYSTERY")
        self.assertEqual(result.length,"SHORT")
        self.assertEqual(result.french,"PREFER")
        self.assertTrue(result.avoid_gore)
        self.assertTrue(result.only_finished)
        self.assertEqual(changes,["avoid_gore","only_finished"])
        self.assertFalse(more)

    def test_more_and_reset_on_structured_dialogue(self):
        prior=AdvisorContext(mood="ACTION",french="REQUIRE",length="LONG")
        cont,changes,more=parse_intent_response('{"updates":{},"more":true,"reset":false}',prior)
        self.assertEqual(cont.mood,"ACTION")
        self.assertEqual(changes,[])
        self.assertTrue(more)
        clear,changes,more=parse_intent_response(
            '{"updates":{"mood":"COMFORT"},"more":false,"reset":true}',prior)
        self.assertEqual(clear.mood,"COMFORT")
        self.assertEqual(clear.length,"ANY")
        self.assertEqual(clear.french,"ANY")
        self.assertIn("reset",changes)
        self.assertFalse(more)

    def test_rejects_untrusted_model_inventions_or_code(self):
        examples=[
            '{"updates":{"sql":"DROP TABLE manga"},"more":false,"reset":false}',
            '{"updates":{"manga_id":123},"more":false}',
            '{"updates":{"genre":"gore"},"more":false}',
            '{"updates":{"min_score":14},"more":false}',
            '{"updates":{"avoid_horror":"yes"},"more":false}',
            '{"updates":{"mood":"SUPERPOPULAR"},"more":false}',
            '{"updates":{"narrative_preferences":["REAL","SPOILER"]}}',
            '{"updates":{"length":null}}',
            '{"updates":null}',
            'Sure, here are 3 manga!',
            '["something"]',
            '{"updates":{},"more":"true"}',
        ]
        for raw in examples:
            with self.subTest(raw=raw):
                with self.assertRaises(LocalAiUnavailable):
                    parse_intent_response(raw,AdvisorContext())

    def test_model_can_clear_constraints_and_never_infer_complete_editions(self):
        original=AdvisorContext(mood="MYSTERY",avoid_horror=True,
                                preferred_edition_kind="DELUXE",require_edition_kind=True)
        updated,changes,more=parse_intent_response(
            '{"updates":{"preferred_edition_kind":null,"avoid_horror":false},'
            '"reset":false,"more":false}',original)
        self.assertIsNone(updated.preferred_edition_kind)
        self.assertFalse(updated.require_edition_kind)
        self.assertFalse(updated.avoid_horror)

    def test_available_model_probe_is_local_and_explicit(self):
        with patch.dict(os.environ,{"OLLAMA_ENABLED":"true","OLLAMA_MODEL":"qwen2.5:3b"}):
            with patch("urllib.request.urlopen",return_value=FakeResponse(
                b'{"models":[{"name":"qwen2.5:3b"}]}'
            )) as mocked:
                status=ai_status()
                self.assertEqual(status["mode"],"local_ai")
                self.assertTrue(status["available"])
                self.assertIn("/api/tags",mocked.call_args.args[0].full_url)
            with patch("urllib.request.urlopen",side_effect=ConnectionError):
                self.assertEqual(ai_status()["mode"],"guided")

    def test_validated_model_json_does_not_make_up_manga(self):
        result=json.dumps({"response":json.dumps({
            "updates":{"mood":"MYSTERY","avoid_gore":True,
                       "narrative_preferences":["INVESTIGATION"]},
            "more":False,"reset":False
        })}).encode()
        with patch.dict(os.environ,{"OLLAMA_ENABLED":"true"}):
            with patch("urllib.request.urlopen",return_value=FakeResponse(result)) as mocked:
                context,changes,more=interpret_with_ollama(
                    "Une vraie enquête, sans gore",AdvisorContext())
                self.assertEqual(context.mood,"MYSTERY")
                self.assertTrue(context.avoid_gore)
                self.assertEqual(context.narrative_preferences,["INVESTIGATION"])
                self.assertEqual(changes,["avoid_gore","mood","narrative_preferences"])
                request=mocked.call_args.args[0]
                self.assertIn("/api/generate",request.full_url)
                body=json.loads(request.data)
                self.assertEqual(body["format"],"json")
                self.assertFalse(body["stream"])
                self.assertNotIn("manga_id",body["prompt"])
                self.assertNotIn("sql",body["prompt"].lower())
                self.assertNotIn("user_manga_library",body["prompt"])

if __name__=="__main__":
    unittest.main()
