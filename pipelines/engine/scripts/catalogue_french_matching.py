"""French-market bibliographic matching policy for Mangadvisor's read-only benchmark.

A sample from the user's declared inventory defaults to FR-language/print
publication as a *search target*, not a claim of ISBN ownership. Generic
catalogue records are international and have no such market constraint.

No network calls, SQL writes, or automatic work/edition linking are performed.
The title sent to an API is supplied only by the caller, never by this module.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from pipelines.engine.scripts.benchmark_manga_sources import title_key


def tidy(text: Any, size: int = 100) -> str:
    return str(text or "").strip()[:size]


def normalized(text: Any) -> str:
    value = unicodedata.normalize("NFKD", tidy(text, 180).casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def edition_family(text: str) -> str | None:
    """Recognize explicit edition clues; never equate different named formats."""
    key = normalized(text)
    for label, patterns in (
        ("pastel", ("pastel",)),
        ("deluxe", ("deluxe", "delux")),
        ("perfect", ("perfect",)),
        ("kanzenban", ("kanzenban",)),
        ("integrale", ("integrale", "integral")),
        ("collector", ("collector", "collectors")),
        ("prestige", ("prestige",)),
        ("double", ("double",)),
        ("standard", ("standard", "classique", "simple")),
    ):
        if any(re.search(r"(?:^| )" + re.escape(word) + r"(?: |$)", key)
               for word in patterns):
            return label
    return None


def work_kind(format_text: Any) -> str | None:
    key = normalized(format_text)
    if not key:
        return None
    if re.search(r"\bdoujin|\bfanzine", key):
        return "doujinshi"
    if re.search(r"\bartbook|\bart book|\billustration", key):
        return "artbook"
    if re.search(r"\blight novel|\broman|\bnovel|\bbook\b|\bln\b", key):
        return "novel"
    if re.search(r"\bguide|\bdatabook|\bfanbook", key):
        return "guide"
    if re.search(r"\bmanhwa", key):
        return "manhwa"
    if re.search(r"\bmanhua", key):
        return "manhua"
    if re.search(r"\bmanga|\bseinen|\bshonen|\bshounen|\bshojo|\bshoujo", key):
        return "manga"
    return None


def enrich_sample_targets(conn: Any, selected: list[dict]) -> list[dict]:
    """Read only original *edition/format declarations* for sampled library.

    No source keys, quantities, ISBN inventory claims, or private notes are
    selected. French is an explicit editable market assumption, not a fact.
    Preserve multiple declared editions for the same work as distinct targets.
    """
    result = []
    inventory_titles = [
        row["title"] for row in selected if row["origin"] in ("pending", "owned")
    ]
    by_key: dict[tuple[str, str], dict[str, list[str]]] = {}
    if inventory_titles:
        sql_queries = [
            ("""SELECT COALESCE(NULLIF(TRIM(work_declared),''),entry_title) AS title,
                       edition_declared,format_hint
                FROM user_manga_inventory_pending
                WHERE user_id=1
                  AND COALESCE(NULLIF(TRIM(work_declared),''),entry_title) = ANY(%s)
                ORDER BY saved_at,source_key""", "pending"),
            ("""SELECT m.title, d.edition_declared,d.format_hint
                FROM user_manga_inventory_declaration d
                JOIN manga m ON m.id=d.manga_id
                WHERE d.user_id=1 AND m.title = ANY(%s)
                ORDER BY m.id,d.edition_key""", "owned"),
        ]
        with conn.cursor() as cur:
            for sql, origin in sql_queries:
                cur.execute(sql, (inventory_titles,))
                for raw in cur.fetchall():
                    key = (origin, title_key(raw.get("title") or ""))
                    dest = by_key.setdefault(key, {"edition_targets": [], "format_hints": []})
                    for field, value in (("edition_targets", raw.get("edition_declared")),
                                         ("format_hints", raw.get("format_hint"))):
                        item = tidy(value)
                        if item and item not in dest[field] and len(dest[field]) < 12:
                            dest[field].append(item)
    for record in selected:
        row = dict(record)
        origin = row["origin"]
        collection = origin in ("pending", "owned")
        row["market_target"] = "FR_PRINT" if collection else "INTERNATIONAL"
        row["market_target_basis"] = (
            "USER_COLLECTION_DEFAULT_UNVERIFIED" if collection
            else "GENERAL_CATALOGUE_NOT_RESTRICTED")
        row.update(by_key.get((origin, title_key(row["title"])),
                              {"edition_targets": [], "format_hints": []}))
        result.append(row)
    return result


def identity_review(sample: dict, candidate: dict | None, *,
                    ambiguous: bool = False) -> dict:
    """Evidence score, NOT a probability; absence of known author cannot pass."""
    if not candidate:
        return {"score": 0, "status": "NO_CANDIDATE",
                "signals": [], "type_evidence": "UNKNOWN"}
    strength = candidate.get("evidence")
    score = {"SAME_MAL_ID": 85, "EXACT_TITLE": 60,
             "SUGGESTION_ONLY": 15}.get(strength, 0)
    signs = [strength] if strength else []
    expected_types = {work_kind(f) for f in sample.get("format_hints", [])}
    expected_types.discard(None)
    observed_type = work_kind(candidate.get("format"))
    type_evidence = "UNVERIFIED_TYPE"
    if expected_types and observed_type:
        if observed_type in expected_types:
            score = min(90, score + 10)
            signs.append("DECLARED_WORK_TYPE_MATCH")
            type_evidence = "MATCH"
        else:
            score = max(0, score - 40)
            signs.append("DECLARED_WORK_TYPE_CONFLICT")
            type_evidence = "CONFLICT"
    elif candidate.get("warning"):
        score = max(0, score - 25)
        signs.append("DERIVATIVE_WARNING")
        type_evidence = "WARNING"
    status = ("REVIEW_AMBIGUOUS" if ambiguous else
              "REVIEW_TYPE_CONFLICT" if type_evidence == "CONFLICT" else
              "REVIEW_IDENTIFIER" if strength == "SAME_MAL_ID" else
              "REVIEW_TITLE_ONLY")
    return {"score": score, "status": status, "signals": signs,
            "type_evidence": type_evidence,
            "reference_author": "NOT_PRESENT_IN_SAMPLE"}


def edition_review(sample: dict, detail: dict | None) -> dict:
    """Measure evidence for a *French print publication* of this work.

    No volume belongs to the user's library unless the user later verifies
    the correct ISBN/edition. A missing edition declaration remains unknown,
    not standard by default.
    """
    target = sample.get("market_target", "INTERNATIONAL")
    if target != "FR_PRINT":
        return {"score": None, "status": "NOT_APPLICABLE_INTERNATIONAL",
                "signals": [], "french_print_isbns": [],
                "declared_editions": []}
    declarations = [
        tidy(x) for x in sample.get("edition_targets", []) if tidy(x)
    ]
    target_families = {x for ed in declarations if (x := edition_family(ed))}
    if not detail or detail.get("status") not in (None, "OK"):
        return {"score": 0, "status": "NOT_EVALUATED_NO_DETAIL",
                "signals": [], "french_print_isbns": [],
                "declared_editions": declarations}
    editions = detail.get("editions") or []
    refs = detail.get("book_references") or []
    fr_print = [ed for ed in editions if isinstance(ed, dict) and
                str(ed.get("lang") or "").lower() == "fr" and
                str(ed.get("medium") or "").lower() == "print"]
    isbn_refs = [r for r in refs if isinstance(r, dict) and
                 str(r.get("lang") or "").lower() == "fr" and
                 str(r.get("medium") or "").lower() == "print" and
                 r.get("isbn13")]
    labels = [str(x.get("edition") or "") for x in fr_print]
    labels.extend(str(x.get("edition_label") or "") for x in isbn_refs)
    found_families = {x for label in labels if (x := edition_family(label))}
    signs = []
    score = 0
    if fr_print or isbn_refs:
        signs.append("FR_PRINT_PUBLICATION_PRESENT")
        score += 50
    if isbn_refs:
        signs.append("FR_PRINT_BIBLIOGRAPHIC_ISBN_PRESENT")
        score += 15
    matched_families = target_families & found_families
    missing_families = target_families - found_families
    if target_families:
        if matched_families:
            # Two declared variants (Pastel + Deluxe) cannot both be marked
            # found merely because one Deluxe listing exists.
            score += (25 * len(matched_families)) // len(target_families)
            signs.append("DECLARED_EDITION_FAMILY_PRESENT")
            if missing_families:
                signs.append("SOME_DECLARED_EDITION_FAMILIES_UNCONFIRMED")
        elif found_families:
            signs.append("DECLARED_EDITION_NOT_FOUND_AMONG_CANDIDATES")
            # Do not assert that an edition is absent from the API globally.
            score = min(score, 25)
        else:
            signs.append("EDITION_LABEL_NOT_COMPARABLE")
    elif declarations:
        signs.append("EDITION_DECLARED_NOT_RECOGNIZED")
    else:
        signs.append("EXACT_EDITION_NOT_DECLARED")
    if not (fr_print or isbn_refs):
        status = "NO_FR_PRINT_EVIDENCE"
    elif "SOME_DECLARED_EDITION_FAMILIES_UNCONFIRMED" in signs:
        status = "FR_PRINT_PARTIAL_EDITION_MATCH_REVIEW"
    elif "DECLARED_EDITION_FAMILY_PRESENT" in signs:
        status = "FR_PRINT_EDITION_CANDIDATE_REVIEW"
    elif "DECLARED_EDITION_NOT_FOUND_AMONG_CANDIDATES" in signs:
        status = "FR_PRINT_EDITION_CONFLICT_REVIEW"
    elif "EDITION_LABEL_NOT_COMPARABLE" in signs or declarations:
        status = "FR_PRINT_EDITION_UNCONFIRMED"
    else:
        status = "FR_PRINT_WORK_FOUND_EDITION_UNKNOWN"
    return {"score": score, "status": status, "signals": signs,
            "french_print_isbns": list(dict.fromkeys(
                str(r["isbn13"]) for r in isbn_refs))[:20],
            "declared_editions": declarations,
            "candidate_edition_families": sorted(found_families),
            "matched_declared_families": sorted(matched_families),
            "unconfirmed_declared_families": sorted(missing_families),
            "isbn_ownership_verified": False}


def review_entry(sample: dict, provider_result: dict) -> dict:
    """Separate work and edition evidence, preserving competing candidates."""
    candidates = provider_result.get("candidates") or []
    first = candidates[0] if candidates else None
    status = provider_result.get("status", "NO_MATCH")
    work = identity_review(sample, first, ambiguous=status == "AMBIGUOUS")
    evidence = provider_result.get("details")
    edition = edition_review(sample, evidence)
    reviewed = []
    for candidate in provider_result.get("competing_details") or []:
        related = next((x for x in candidates if x.get("id") == candidate.get("id")), None)
        reviewed.append({
            "id": candidate.get("id"),
            "work": identity_review(sample, related, ambiguous=True),
            "edition": edition_review(sample, candidate.get("details")),
        })
    return {"market_target": sample.get("market_target", "INTERNATIONAL"),
            "market_target_basis": sample.get("market_target_basis"),
            "edition_targets": sample.get("edition_targets") or [],
            "format_hints": sample.get("format_hints") or [],
            "work": work, "edition": edition,
            "competing_evidence": reviewed,
            "automatic_link": False,
            "work_author_match": "NOT_COMPUTABLE_WITHOUT_REFERENCE_AUTHOR"}
