"""Public catalogue work-graph rebuild runnable in the lean API Docker image.

The production API image deliberately contains `apps/api`, not
`pipelines/engine`. This entrypoint depends only on that installed code.
The larger engine command is kept for explicitly requested third-party APIs.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from apps.api.app.catalogue_source_graph import ensure_schema, rebuild_legacy_sources
from apps.api.app.bnf_batch import connect_database


def public_report(conn: Any) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.catalogue_work') IS NOT NULL AS ready")
        ready=bool(cur.fetchone()["ready"])
        cur.execute("SELECT count(*) AS n FROM manga")
        total=int(cur.fetchone()["n"])
        if not ready:
            return {"legacy_works":total,"source_graph_initialized":0}
        cur.execute("""SELECT
            (SELECT count(*) FROM catalogue_work) AS works,
            (SELECT count(*) FROM catalogue_work WHERE legacy_manga_id IS NULL) AS non_mal_works,
            (SELECT count(*) FROM catalogue_title_claim) AS titles,
            (SELECT count(*) FROM catalogue_title_claim
             WHERE evidence_status='COLLISION_REVIEW') AS title_collisions,
            (SELECT count(*) FROM catalogue_title_claim
             WHERE claim_kind='UNVERIFIED_SYNONYM'
               AND evidence_status='DISCOVERY_ONLY') AS unverified_synonyms,
            (SELECT count(*) FROM catalogue_title_claim
             WHERE language_code='fr') AS french_title_claims,
            (SELECT count(DISTINCT work_id) FROM catalogue_title_claim
             WHERE language_code='fr'
               AND evidence_status NOT IN ('REJECTED','COLLISION_REVIEW'))
               AS works_with_sourced_french_titles,
            (SELECT count(*) FROM catalogue_title_claim
             WHERE source_name='WIKIDATA_P4087' AND language_code='fr')
               AS wikidata_french_titles,
            (SELECT count(*) FROM catalogue_title_claim
             WHERE source_name='SCRINIS_FR' AND language_code='fr')
               AS scrinis_french_titles,
            (SELECT count(*) FROM catalogue_work_identifier
             WHERE identity_status='COLLISION_REVIEW') AS identifier_conflicts,
            (SELECT count(*) FROM catalogue_work_relation) AS typed_relations,
            (SELECT count(*) FROM catalogue_book_claim) AS book_candidates,
            (SELECT count(*) FROM catalogue_book_claim
             WHERE evidence_status='MULTI_WORK_ISBN_REVIEW') AS cross_work_book_claims
        """)
        counts=dict(cur.fetchone())
        return {"legacy_works":total,"source_graph_initialized":1,
                **{k:int(v) for k,v in counts.items()}}


def main(argv: list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(
        description="Rebuild the public catalogue source graph in the API container")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report-only",action="store_true")
    mode.add_argument("--apply",action="store_true")
    args=parser.parse_args(argv)
    with connect_database() as conn:
        before=public_report(conn)
        if args.apply:
            ensure_schema(conn)
            rebuild_legacy_sources(conn)
            conn.commit()
        after=public_report(conn)
    print(json.dumps({
        "mode":"APPLIED" if args.apply else "READ_ONLY",
        "before":before,
        "after":after,
        "user_library_modified":False,
        "original_jikan_modified":False,
        "legacy_manga_modified":False,
        "external_api_requests":0,
    },ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
