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


def _known_title_suffix(title: str, known_titles: list[str]) -> str | None:
    """Find a boundary-safe suffix of a known title, longest alias first.

    Only aliases already trusted by the caller may establish a title prefix.
    A prefix match remains a *candidate*, not a verified work identity.
    """
    candidate = normalized(title)
    titles = sorted(
        {normalized(t) for t in known_titles if len(normalized(t)) >= 3},
        key=len, reverse=True,
    )
    for root in titles:
        if candidate == root:
            return ""
        if candidate.startswith(root) and len(candidate) > len(root):
            tail = candidate[len(root):]
            if not tail[0].isalnum():
                return tail.strip(" .,:;/-")
    return None


def work_candidate_status(title: str, known_titles: list[str]) -> str:
    """Classify obvious off-topic and derivative titles without auto-linking."""
    suffix = _known_title_suffix(title, known_titles)
    if suffix is None:
        return "REJECT_DIFFERENT_WORK"
    if not suffix:
        return "REVIEW_UNNUMBERED"
    # Derivative descriptions sometimes arrive after a colon or in brackets.
    # Keep them visible for human review, never register them as ordinary tomes.
    descriptor = suffix.strip(" ()[]{}-:;,.")
    if re.search(
        r"\b(?:illustrations? file|art\s?book|guide\s?book|"
        r"official guide|guide officiel|fan\s?book|data\s?book|"
        r"roman|novel|color walk|character book|anime comics)\b",
        descriptor,
    ):
        return "REVIEW_DERIVATIVE"
    if re.match(r"^(?:of |des |de |du |and |et )", descriptor):
        return "REJECT_DIFFERENT_WORK"
    if re.match(r"^(?:tome\s*\d+|vol(?:ume)?\.?\s*\d+|t\.?\s*\d+|\d+\b)", descriptor):
        return "REVIEW_VOLUME_CANDIDATE"
    if re.match(r"^ed(?:ition|\.)?\b", descriptor):
        return "REVIEW_EDITION_CANDIDATE"
    # A short author credit after an exact title is still unnumbered.
    # A DIFFERENT substantive subtitle (e.g. Naruto vs Hitachi) is NOT
    # positive work/title evidence merely because a series name prefixes it.
    if not descriptor or suffix.lstrip().startswith("/") or re.match(
        r"^(?:\s*/\s*|\s*\(\s*(?:auteur|dessin|scenario)\b)",
        suffix, re.I
    ):
        return "REVIEW_UNNUMBERED"
    return "REVIEW_OTHER_TITLE"


def volume_from_known_title(title: str, known_titles: list[str]) -> int | None:
    """Recognize bare tome numbers only after an explicit trusted work title.

    For example 'One Piece 01' => 1; 'One Piece 2024' and 'One Piece 3D2Y'
    deliberately yield no numbered volume. Never infer edition or ownership.
    """
    suffix = _known_title_suffix(title, known_titles)
    if suffix is None or not suffix:
        return None
    match = re.match(
        r"^(?:tome\s*|vol(?:ume)?\.?\s*|t\.?\s*)?"
        r"0*([1-9]\d{0,2})(?=$|[\s.,:;/()\-])",
        suffix,
    )
    return int(match.group(1)) if match else None


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


def author_correspondence(author: Any, known_authors: list[str] | None) -> str:
    """Independent author hint, not a licence to link an ISBN or work.

    Catalogued contributors can include translators and editors; a missing
    token match is therefore REVIEW rather than a definitive work conflict.
    """
    if not isinstance(author, str) or not author.strip() or not known_authors:
        return "UNVERIFIED"
    source = set(re.findall(r"[a-z0-9]+", normalized(author)))
    usable = []
    for name in known_authors:
        tokens = set(re.findall(r"[a-z0-9]+", normalized(name)))
        if len(tokens) >= 2 and sum(len(x) for x in tokens) >= 6:
            usable.append(tokens)
    if not source or not usable:
        return "UNVERIFIED"
    return "MATCH" if any(tokens <= source for tokens in usable) else "REVIEW_DIFFERENT_CREDITS"


def classify_candidate(
    row: dict[str, Any], known_titles: list[str],
    known_authors: list[str] | None = None,
) -> dict[str, Any]:

    work = work_candidate_status(str(row.get("title_fr") or ""), known_titles)
    lang = language_status(row.get("language_recorded"))
    edition = edition_status(str(row.get("title_fr") or ""),
                             str(row.get("edition_kind_suggested") or "UNKNOWN"))
    # Numbering on another work or a derivative is not a volume of this manga.
    # Keep the documentary candidate for review but do not suggest a tome.
    volume = None
    if work not in {"REJECT_DIFFERENT_WORK", "REVIEW_DERIVATIVE",
                    "REVIEW_OTHER_TITLE"}:
        volume = volume_from_title(str(row.get("title_fr") or ""))
        if volume is None and work == "REVIEW_VOLUME_CANDIDATE":
            volume = volume_from_known_title(str(row.get("title_fr") or ""), known_titles)
    eligible = work in {"REVIEW_VOLUME_CANDIDATE", "REVIEW_EDITION_CANDIDATE",
                        "REVIEW_UNNUMBERED"}
    return {
        "isbn13": row.get("isbn13"),
        "title_fr": row.get("title_fr"),
        "publisher_fr": row.get("publisher_fr"),
        "author_fr": row.get("author_fr"),
        "release_date_text": row.get("release_date_text"),
        "source_name": row.get("source_name"),
        "source_url": row.get("source_url"),
        "language_recorded": row.get("language_recorded"),
        "work_status": work,
        "language_status": lang,
        "author_evidence": author_correspondence(row.get("author_fr"), known_authors),
        "edition_suggested": edition,
        "volume_suggested": volume,
        "registration_ready": False,
        "needs_manual_review": eligible and lang != "NON_FRENCH_DECLARED",
        "reason": "L'ISBN reste candidat : ni oeuvre, ni langue, ni edition n'est automatiquement validee.",
    }
