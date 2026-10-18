"""Only report narrative signals backed by literal catalog fields.

Evidence is *not* a literary analysis: a matching tag or a word present in the
synopsis supports a search hint, not a claim about tone, maturity or storyline.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

NARRATIVE_CONCEPTS = ("INVESTIGATION", "PSYCHOLOGICAL", "SURVIVAL")

# Specific catalog tags, intentionally avoiding broad "similar enough" tags.
CONCEPT_TAGS: dict[str, tuple[str, ...]] = {
    "INVESTIGATION": ("Detective",),
    "PSYCHOLOGICAL": ("Psychological",),
    "SURVIVAL": ("Survival",),
}

# Match explicit lexical evidence, not arbitrary title or synopsis guesses.
CONCEPT_WORDS: dict[str, tuple[str, ...]] = {
    "INVESTIGATION": (
        r"\benquet\w*\b", r"\binvestigat\w*\b", r"\bdetectiv\w*\b",
        r"\benquir\w*\b",
    ),
    "PSYCHOLOGICAL": (
        r"\bpsycholog\w*\b", r"\bpsychological\b",
    ),
    "SURVIVAL": (
        r"\bsurvi\w*\b", r"\bsurviv\w*\b", r"\bsurvival\b",
    ),
}

def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))

def narrative_matches(
    item: dict[str, Any], requested: Iterable[str]
) -> list[dict[str, str]]:
    """One grounded signal per concept; favor a catalog tag over synopsis words."""
    evidence: list[dict[str, str]] = []
    valid = dict.fromkeys(name for name in requested if name in CONCEPT_TAGS)
    genres_and_themes = [
        tag for kind in ("genres", "themes") for tag in (item.get(kind) or [])
        if isinstance(tag, str)
    ]
    synopsis = str(item.get("synopsis") or "")
    normalized_synopsis = fold(synopsis)
    for concept in valid:
        accepted = {fold(tag) for tag in CONCEPT_TAGS[concept]}
        tag = next((tag for tag in genres_and_themes if fold(tag) in accepted), None)
        if tag:
            evidence.append({"concept": concept, "source": "catalog_tag", "matched": tag})
            continue
        for pattern in CONCEPT_WORDS[concept]:
            found = re.search(pattern, normalized_synopsis)
            if found:
                # Only disclose the matching word, never an unsupported paraphrase.
                evidence.append({"concept": concept, "source": "synopsis_word",
                                 "matched": found.group(0)[:40]})
                break
    return evidence
