"""Public manga-catalogue multiword search: verified titles before token noise.

The existing optional Meilisearch index may rank the French expression
"Adieu Eri" as titles containing "Adieu" while omitting "Sayonara Eri".
For multiword names, inspect whole WORD matches across canonical titles,
source-scoped aliases and Wikidata, then return authoritative manga IDs.
No network request, private inventory read or catalogue write.
"""
from __future__ import annotations

from typing import Any

from apps.api.app.inventory_resolution import DISCOVERY_SQL
from apps.api.app.matching_quality import rank_candidates, search_patterns
from apps.api.app.reconciliation_engine import discovery_terms

MIN_RELEVANCE = 18


def ranked_catalogue_ids(cursor: Any, query: str) -> list[int] | None:
    """None means use the existing single-term Meili/SQL search flow.

    Empty list means a multiword query has no credible *local* results;
    do not fall back to the unrelated Meili fuzzy title guesses.
    """
    words = discovery_terms(query)
    if len(words) < 2:
        return None
    cursor.execute(DISCOVERY_SQL, {"patterns": search_patterns(words)})
    rows = [dict(row) for row in cursor.fetchall()]
    # A partial discovery list must never be labelled a unique identity.
    ranked = rank_candidates(query, rows[:100], total_limited=len(rows) > 100,
                             display_limit=100)
    return [
        int(candidate["id"]) for candidate in ranked["candidates"]
        if candidate["ranking"]["score"] >= MIN_RELEVANCE
    ]
