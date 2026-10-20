"""One-click, resumable enrichment of *linked* personal manga works only.

The user's pending physical inventory rows have no trustworthy manga_id and
are NOT guessed or sent to providers. Existing Wikidata and BnF collectors
write ONLY to their additive source-evidence tables; no ISBN is confirmed.
"""
from __future__ import annotations

import argparse
import math
import time
from typing import Any, Callable

from apps.api.app.bnf_batch import (
    connect_database, run_batch as run_bnf_batch, MAX_BATCH as BNF_MAX_BATCH,
)
from apps.api.app.wikidata_enrichment import (
    run_batch as run_wikidata_batch, MAX_BATCH as WIKIDATA_MAX_BATCH,
)

MAX_WORKS = 250
DEFAULT_WORKS = 80
# One multi-ID Wikidata call, one bounded BnF batch; small pauses between lots.
DEFAULT_BNF_BATCH = 10
BETWEEN_BATCH_DELAY = 1.5

LINKED_SQL = """
SELECT m.id
FROM manga m
WHERE EXISTS (
    SELECT 1 FROM user_manga_inventory_declaration d
    WHERE d.user_id=%(user_id)s AND d.manga_id=m.id
) OR EXISTS (
    SELECT 1 FROM user_manga_library l
    WHERE l.user_id=%(user_id)s AND l.manga_id=m.id
)
ORDER BY CASE WHEN EXISTS (
    SELECT 1 FROM user_manga_inventory_declaration d
    WHERE d.user_id=%(user_id)s AND d.manga_id=m.id
) THEN 0 ELSE 1 END, m.popularity ASC NULLS LAST, m.id ASC
LIMIT %(limit)s
"""

PENDING_SQL = """
SELECT COUNT(*)::int AS count
FROM user_manga_inventory_pending
WHERE user_id=%(user_id)s
"""


def linked_library_scope(
    factory: Callable[..., Any], *, user_id: int = 1, max_works: int = DEFAULT_WORKS
) -> dict[str, Any]:
    """Never widen a user's request to the full catalogue or invent matches."""
    if type(user_id) is not int or user_id <= 0:
        raise ValueError("Identifiant utilisateur incorrect.")
    if type(max_works) is not int or not 1 <= max_works <= MAX_WORKS:
        raise ValueError(f"Nombre de mangas : entre 1 et {MAX_WORKS}.")
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(LINKED_SQL, {"user_id": user_id, "limit": max_works + 1})
            rows = list(cur.fetchall())
            cur.execute(PENDING_SQL, {"user_id": user_id})
            pending = int(cur.fetchone()["count"])
    return {
        "ids": [int(r["id"]) for r in rows[:max_works]],
        "truncated": len(rows) > max_works,
        "pending": pending,
    }


def run_library_enrichment(
    factory: Callable[..., Any],
    *, max_works: int = DEFAULT_WORKS,
    user_id: int = 1,
    include_bnf: bool = True,
    wikidata_batch: Callable[..., dict[str, int]] = run_wikidata_batch,
    bnf_batch: Callable[..., dict[str, int]] = run_bnf_batch,
    sleep: Callable[[float], Any] = time.sleep,
) -> dict[str, Any]:
    """Run both bounded providers over a stable, verified scope.

    Every provider selects only unprocessed / expired work IDs. Re-running
    remains additive/idempotent. A provider with a whole failed batch stops,
    so outages do not hammer free public services.
    """
    scope = linked_library_scope(factory, user_id=user_id, max_works=max_works)
    ids: list[int] = scope["ids"]
    report: dict[str, Any] = {
        "linked_works": len(ids),
        "scope_limited": scope["truncated"],
        "pending_inventory": scope["pending"],
        "sources": {},
        "failed_sources": [],
    }
    if scope["pending"]:
        print(
            f"ATTENTION : {scope['pending']} ligne(s) de mangatheque physique "
            "sans correspondance catalogue. AUCUN manga ni ISBN n'est devine.",
            flush=True,
        )
    if not ids:
        print("Aucune oeuvre de ta bibliotheque n'est liee au catalogue.", flush=True)
        return report

    providers = [("wikidata", wikidata_batch, WIKIDATA_MAX_BATCH)]
    if include_bnf:
        providers.append(("bnf", bnf_batch, DEFAULT_BNF_BATCH))

    for name, collector, page_size in providers:
        summary: dict[str, int] = {"selected": 0}
        halted = False
        # At most ceil(N / batch_size) + 1 selections; every selected work
        # is checkpointed in the source's attempt table.
        for page in range(math.ceil(len(ids) / page_size) + 1):
            if page:
                sleep(BETWEEN_BATCH_DELAY)
            print(f"[{name}] Lot {page + 1}, au plus {page_size} oeuvres...", flush=True)
            try:
                result = collector(
                    factory, limit=page_size, refresh=False, target_ids=ids
                )
            except (TimeoutError, OSError, ValueError) as exc:
                print(f"[{name}] Traitement interrompu : {type(exc).__name__}", flush=True)
                halted = True
                break
            count = int(result.get("selected", 0))
            for key, value in result.items():
                if isinstance(value, int) and key != "selected":
                    summary[key] = summary.get(key, 0) + value
            summary["selected"] += count
            print(
                f"[{name}] {count} oeuvre(s) traitees dans ce lot ; "
                + ", ".join(f"{k}={v}" for k, v in result.items() if k != "selected"),
                flush=True,
            )
            if count == 0:
                break
            if count > page_size:
                raise ValueError("Le fournisseur a depasse la limite du lot.")
            if result.get("error", 0) == count and count:
                halted = True
                print(
                    f"[{name}] Source indisponible pour tout le lot. "
                    "Arret des appels a ce fournisseur, reprise possible plus tard.",
                    flush=True,
                )
                break
        summary["halted"] = int(halted)
        if halted:
            report["failed_sources"].append(name)
        report["sources"][name] = summary
    return report


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrichir la mangatheque liee, sans ecrire dans l'inventaire.")
    parser.add_argument("--max-works", type=int, default=DEFAULT_WORKS)
    parser.add_argument("--skip-bnf", action="store_true",
                        help="Wikidata uniquement : evite les recherches bibliographiques BnF.")
    args = parser.parse_args(argv)
    if not 1 <= args.max_works <= MAX_WORKS:
        parser.error(f"--max-works doit etre entre 1 et {MAX_WORKS}")
    print("Mangadvisor : enrichissement de la mangatheque liee au catalogue.")
    print("Aucune edition, ISBN, note, progression ou declaration utilisateur n'est modifiee.")
    result = run_library_enrichment(
        connect_database, max_works=args.max_works, include_bnf=not args.skip_bnf
    )
    print(
        "Bilan collection : "
        f"{result['linked_works']} oeuvres liees ; "
        f"{result['pending_inventory']} lignes d'inventaire en attente"
        + (" ; limite de lot atteinte" if result["scope_limited"] else ""),
        flush=True,
    )
    for source, stats in result["sources"].items():
        print(
            f"  {source} : "
            + ", ".join(f"{k}={v}" for k, v in stats.items()), flush=True
        )
    if result["failed_sources"]:
        print(
            "ECHEC PARTIEL : fournisseur(s) indisponible(s) : "
            + ", ".join(result["failed_sources"])
            + ". Relancer plus tard : les lots traites sont conserves.",
            flush=True,
        )
        return 1
    print("Enrichissement termine. Les ISBN BnF restent des CANDIDATS a verifier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
