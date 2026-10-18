"""No user data is sent to a translator by default; synopsis is public catalog text."""
import os
import unittest
from unittest.mock import patch

from apps.api.app.localization import localized_synopsis, _translate_public_catalog_text


class LocalizationTests(unittest.TestCase):
    def tearDown(self):
        _translate_public_catalog_text.cache_clear()

    def test_english_synopsis_kept_as_original(self):
        self.assertEqual(
            localized_synopsis("An English story.", "en"),
            {"text": "An English story.", "translated": False, "source_lang": "en", "target_lang": "en"},
        )

    def test_french_falls_back_honestly_without_provider(self):
        with patch.dict(os.environ, {"LIBRETRANSLATE_URL": ""}):
            self.assertEqual(
                localized_synopsis("An English story.", "fr"),
                {"text": "An English story.", "translated": False, "source_lang": "en", "target_lang": "en"},
            )

    def test_absent_synopsis(self):
        with patch.dict(os.environ, {"LIBRETRANSLATE_URL": ""}):
            self.assertEqual(localized_synopsis(None, "fr")["text"], "")
            self.assertFalse(localized_synopsis(None, "fr")["translated"])

    def test_translation_flag_only_for_actual_translation(self):
        with patch("apps.api.app.localization._translate_public_catalog_text", return_value="Une histoire."):
            result = localized_synopsis("A story.", "fr")
        self.assertEqual(result["text"], "Une histoire.")
        self.assertTrue(result["translated"])
        self.assertEqual(result["target_lang"], "fr")

    def test_no_unnecessary_remote_call_for_long_synopsis(self):
        with patch.dict(os.environ, {"LIBRETRANSLATE_URL": "http://fake-translate:5000/translate"}):
            self.assertIsNone(_translate_public_catalog_text("A" * 10001, "fr"))


if __name__ == "__main__":
    unittest.main()
