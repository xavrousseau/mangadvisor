"""Bilingual synopsis support.

No external service is contacted unless LIBRETRANSLATE_URL is explicitly configured.
Only catalog synopsis text is sent; library notes and user data are never translated.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class SynopsisTranslationRequest(BaseModel):
    manga_id: int = Field(..., ge=1)
    lang: str = Field(..., pattern=r"^(fr|en)$")


@lru_cache(maxsize=512)
def _translate_public_catalog_text(synopsis: str, lang: str) -> str | None:
    endpoint = os.getenv("LIBRETRANSLATE_URL", "").strip()
    if not endpoint or not synopsis or lang != "fr" or len(synopsis) > 10000:
        return None

    payload = {
        "q": synopsis, "source": "en", "target": lang, "format": "text",
    }
    api_key = os.getenv("LIBRETRANSLATE_API_KEY", "").strip()
    if api_key:
        payload["api_key"] = api_key

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 200:
                return None
            result: dict[str, Any] = json.load(response)
        translation = result.get("translatedText")
        return translation.strip() if isinstance(translation, str) and translation.strip() else None
    except (URLError, HTTPError, TimeoutError, ValueError, OSError, TypeError):
        return None


def localized_synopsis(synopsis: str | None, lang: str) -> dict[str, Any]:
    original = synopsis or ""
    if lang == "en" or not original:
        return {"text": original, "translated": False, "source_lang": "en", "target_lang": lang}
    translation = _translate_public_catalog_text(original, lang)
    return {
        "text": translation or original,
        "translated": bool(translation),
        "source_lang": "en",
        "target_lang": lang if translation else "en",
    }
