"""Conservative BnF ISBN candidate triage: work, language, edition, volume.

Read-only metadata reasoning. A title-search hit never proves work identity,
French publication, ISBN ownership, or completeness. Preserve the raw record.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from apps.api.app.bnf_edition_audit import volume_from_title


def normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def work_candidate_status(title: str, known_titles: list[str]) -> str:
    """Flag obvious distinct works, not proof that remaining titles match.

    A root title ('Berserk') plus a prose suffix ('of gluttony') is different.
    Exact roots, volume notations, parenthetical editions and bylines remain
    plausible only; publications such as artbooks must be reviewed separately.
    """
    candidate = normalized(title)
    titles = sorted(
        (normalized(t) for t in known_titles if len(normalized(t)) >= 3),
        key=len, reverse=True,
    )
    for root in titles:
        if candidate == root:
            return "REVIEW_UNNUMBERED"
        if not candidate.startswith(root):
            continue
        tail = candidate[len(root):]
        if not tail or tail[0].isalnum():
            continue
        suffix = tail.strip(" .,:;/-")
        if not suffix:
            return "REVIEW_UNNUMBERED"
        if re.match(r"^(of |des |de |du |and |et )", suffix):
            return "REJECT_DIFFERENT_WORK"
        if re.match(r"^(illustrations? file|art ?book|guide ?book|official guide|roman\b|novel\b)", suffix):
            return "REVIEW_DERIVATIVE"
        if re.match(r"^(tome\s*\d+|vol(?:ume)?\.?\s*\d+|t\.?\s*\d+|\d+\b)", suffix):
            return "REVIEW_VOLUME_CANDIDATE"
        if re.match(r"^\(?ed(?:ition|\.)?\b", suffix):
            return "REVIEW_EDITION_CANDIDATE"
        return "REVIEW_UNNUMBERED"
    return "REJECT_DIFFERENT_WORK"


def language_status(value: Any) -> str:
    """Source-declared language only; French-like publisher is not proof."""
    if not isinstance(value, str) or not value.strip():
        return "UNKNOWN"
    raw = normalized(value)
    codes = set(re.findall(r"[a-z]{2,12}", raw))
    french = bool(codes & {"fre", "fra", "fr", "francais", "french"})
    other = bool(codes & {"eng", "en", "english", "anglais", "jpn", "ja",
                           "japanese", "japonais", "de", "ger", "deu", "allemand",
                           "es", "spa", "espagnol", "it", "ita", "italien"})
    if french and other:
        return "MULTILINGUAL_REVIEW"
    if french:
        return "FRENCH_DECLARED"
    if other:
        return "NON_FRENCH_DECLARED"
    return "UNRECOGNIZED"


def edition_status(title: str, existing: str = "UNKNOWN") -> str:
    text = normalized(title)
    if re.search(r"\b(prestige)\b", text):
        return "PRESTIGE"
    if re.search(r"\b(deluxe)\b", text):
        return "DELUXE"
    if re.search(r"\b(perfect|kanzenban)\b", text):
        return "PERFECT"
    if re.search(r"\bcollector\b", text):
        return "COLLECTOR"
    if re.search(r"\b(integrale|integral)\b", text):
        return "INTEGRAL"
    return existing if existing and existing != "CLASSIC" else "UNKNOWN"


def classify_candidate(row: dict[str, Any], known_titles: list[str]) -> dict[str, Any]:
    work = work_candidate_status(str(row.get("title_fr") or ""), known_titles)
    lang = language_status(row.get("language_recorded"))
    edition = edition_status(str(row.get("title_fr") or ""),
                             str(row.get("edition_kind_suggested") or "UNKNOWN"))
    volume = volume_from_title(str(row.get("title_fr") or ""))
    eligible = work in {"REVIEW_VOLUME_CANDIDATE", "REVIEW_EDITION_CANDIDATE",
                        "REVIEW_UNNUMBERED"}
    return {
        "isbn13": row.get("isbn13"),
        "title_fr": row.get("title_fr"),
        "publisher_fr": row.get("publisher_fr"),
        "language_recorded": row.get("language_recorded"),
        "work_status": work,
        "language_status": lang,
        "edition_suggested": edition,
        "volume_suggested": volume,
        "registration_ready": False,
        "needs_manual_review": eligible and lang != "NON_FRENCH_DECLARED",
        "reason": "L'ISBN reste candidat : ni oeuvre, ni langue, ni edition n'est automatiquement validee.",
    }
