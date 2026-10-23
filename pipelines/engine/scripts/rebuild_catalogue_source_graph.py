"""Rebuild the PUBLIC work graph and optionally enrich specific MAL manga IDs.

Safe workflow:
  python -m pipelines.engine.scripts.rebuild_catalogue_source_graph --report-only
  python -m pipelines.engine.scripts.rebuild_catalogue_source_graph --apply
  python -m pipelines.engine.scripts.rebuild_catalogue_source_graph --apply \
     --mal-ids 145863,598 --providers anilist,kitsu,mangadex,wikidata

No network unless --providers was explicitly supplied. Each provider request
is bounded and source IDs must join existing MAL IDs exactly. Nothing touches
user_* tables, manga legacy rows or owned volumes.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Callable

from apps.api.app.catalogue_source_graph import (
    ensure_schema, rebuild_legacy_sources, stage_external_facts,
)
from apps.api.app.international_crosswalk import (
    search_anilist_by_mal_ids, search_kitsu_by_mal,
)
from apps.api.app.mangadex_discovery import (
    search_mangadex, extract_mal_candidates,
)
from apps.api.app.wikidata_reverse import search_wikidata_mal_titles
from apps.api.app.bnf_batch import connect_database

PROVIDERS=frozenset({"anilist","kitsu","mangadex","wikidata"})


def parse_mal_ids(value: str) -> list[int]:
    ids=[]
    for part in value.split(","):
        text=part.strip()
        if not text or not text.isascii() or not text.isdecimal():
            raise ValueError("Expected a comma-delimited list of positive MAL manga IDs.")
        num=int(text)
        if num<1 or num>999999999 or num in ids:
            if num in ids:
                continue
            raise ValueError("Invalid MAL manga ID.")
        ids.append(num)
    if len(ids)>8:
        raise ValueError("At most eight manga may be externally enriched per run.")
    return ids


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
            (SELECT count(*) FROM catalogue_work_identifier
             WHERE identity_status='COLLISION_REVIEW') AS identifier_conflicts,
            (SELECT count(*) FROM catalogue_work_relation) AS typed_relations
        """)
        counts=dict(cur.fetchone())
        return {"legacy_works":total,"source_graph_initialized":1,
                **{k:int(v) for k,v in counts.items()}}


def _local_by_mal(conn: Any, ids: list[int]) -> dict[int,dict]:
    with conn.cursor() as cur:
        cur.execute("""SELECT source_mal_id,title,title_english,title_japanese
                       FROM manga WHERE source_mal_id=ANY(%s)""",(ids,))
        return {int(r["source_mal_id"]):dict(r) for r in cur.fetchall()}


def enrich_selected(conn: Any, ids: list[int], providers: set[str],
                    *, sleep: Callable[[float],None] = time.sleep) -> dict:
    """Only explicit, scoped provider calls. Failures do not invent missing works."""
    if not ids or not providers:
        return {"requests":0,"new_claim_operations":0,"providers":{},
                "identity_merges":0}
    works=_local_by_mal(conn,ids)
    report={"requests":0,"new_claim_operations":0,
            "providers":{},"identity_merges":0}
    if "anilist" in providers:
        response=search_anilist_by_mal_ids(sorted(works))
        count=0
        for item in response.get("items",[]):
            mid=item.get("source_mal_id")
            if mid not in works:
                continue
            outcome=stage_external_facts(
                conn,mid,provider="ANILIST",
                source_id=str(item["anilist_id"]),
                url=item["source_url"],
                titles=item.get("titles"),
                relations=item.get("relations"))
            count+=outcome["stored"]
        report["providers"]["anilist"]={"status":response["status"],"claims_seen":count}
        report["requests"]+=1
        report["new_claim_operations"]+=count
        sleep(2.1)  # Conservative spacing for temporary AniList limits.
    if "kitsu" in providers:
        statuses={}
        for mid in ids:
            if mid not in works:
                continue
            response=search_kitsu_by_mal(mid)
            report["requests"]+=2  # upper-bound; no-result consumes one
            statuses[str(mid)]=response["status"]
            if response["status"] not in (
                "MAL_ANILIST_CROSS_ID_REVIEW","MAL_MAPPING_ONLY",
            ):
                continue
            for candidate in response.get("items",[])[:1]:
                if candidate.get("source_mal_id")!=mid:
                    continue
                outcome=stage_external_facts(
                    conn,mid,provider="KITSU",
                    source_id=str(candidate["kitsu_id"]),
                    url=candidate["source_url"])
                report["new_claim_operations"]+=outcome["stored"]
            sleep(1)
        report["providers"]["kitsu"]=statuses
    if "mangadex" in providers:
        statuses={}
        for mid,work in works.items():
            payload=search_mangadex(work["title"][:100])
            candidates=extract_mal_candidates(payload)
            report["requests"]+=1
            if mid not in candidates:
                statuses[str(mid)]="NO_EXACT_MAL_LINK"
                continue
            item=candidates[mid]
            report["new_claim_operations"]+=stage_external_facts(
                conn,mid,provider="MANGADEX",
                source_id=item["mangadex_id"],url=item["source_url"],
                titles=item.get("titles"))["stored"]
            statuses[str(mid)]="STAGED_EXACT_MAL_LINK"
            sleep(0.5)
        report["providers"]["mangadex"]=statuses
    if "wikidata" in providers:
        statuses={}
        for mid,work in works.items():
            # Wikidata exact title lookup returns Q item AND its P4087 MAL ID.
            result=search_wikidata_mal_titles(work["title"][:100])
            report["requests"]+=1
            matches=[item for item in result.get("items",[])
                     if item.get("source_mal_id")==mid]
            if len(matches)!=1:
                statuses[str(mid)]="AMBIGUOUS_OR_NO_P4087"
                continue
            item=matches[0]
            report["new_claim_operations"]+=stage_external_facts(
                conn,mid,provider="WIKIDATA",
                source_id=item["wikidata_id"],
                url=item["source_url"])["stored"]
            statuses[str(mid)]="STAGED_EXACT_P4087"
            sleep(0.5)
        report["providers"]["wikidata"]=statuses
    return report


def main(argv: list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(
        description="Rebuild public manga source graph, with optional exact-ID checks")
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report-only",action="store_true")
    mode.add_argument("--apply",action="store_true")
    parser.add_argument("--mal-ids",default="")
    parser.add_argument("--providers",default="",
                        help="Opt-in: anilist,kitsu,mangadex,wikidata")
    args=parser.parse_args(argv)
    providers=set(p.strip() for p in args.providers.split(",") if p.strip())
    if providers-PROVIDERS:
        parser.error("Unknown source: "+",".join(sorted(providers-PROVIDERS)))
    if providers and (not args.mal_ids or not args.apply):
        parser.error("Live providers require --apply and explicit --mal-ids")
    try:
        ids=parse_mal_ids(args.mal_ids) if args.mal_ids else []
    except ValueError as exc:
        parser.error(str(exc))
    with connect_database() as conn:
        if args.apply:
            ensure_schema(conn)
            rebuild_legacy_sources(conn)
            # Persist the rebuild before network requests. Provider failures
            # can never roll back the verified source graph itself.
            conn.commit()
            print("Public catalogue graph built, original source tables unchanged.")
        before=public_report(conn)
        external={}
        if providers:
            external=enrich_selected(conn,ids,providers)
            conn.commit()
        after=public_report(conn)
    print(json.dumps({
        "mode":"APPLIED" if args.apply else "READ_ONLY",
        "before_external":before,
        "after":after,
        "external":external,
        "user_library_modified":False,
        "original_jikan_modified":False,
        "legacy_manga_modified":False,
    },ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
