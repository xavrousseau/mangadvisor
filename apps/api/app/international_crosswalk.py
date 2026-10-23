"""Opt-in international manga crosswalk: AniList GraphQL + Kitsu JSON:API.

The returned references are public metadata *claims*, not automatic work
identity links or physical books. Distinguish manga from anime/novel records.
Do not call the providers in normal navigation or mass catalogue updates.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from fastapi import HTTPException

ANILIST_URL = "https://graphql.anilist.co"
KITSU_URL = "https://kitsu.io/api/edge"
MAX_BYTES = 350_000
IDENTIFIER = re.compile(r"^[1-9][0-9]{0,8}$")
ANILIST_QUERY = """
query MangaTitleCrosswalk($search: String!) {
  Page(page: 1, perPage: 12) {
    media(search: $search, type: MANGA, isAdult: false) {
      id idMal type format
      title { romaji english native }
      synonyms
    }
  }
}
"""


def _safe_positive(value: Any) -> int | None:
    if type(value) in (str, int) and IDENTIFIER.fullmatch(str(value)):
        return int(value)
    return None


def _query_title(value: str) -> str:
    title = str(value).strip()
    if not 2 <= len(title) <= 100 or any(ord(char) < 32 for char in title):
        raise ValueError("Manga title must contain 2-100 printable characters.")
    return title


def _read_json(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            body = response.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES:
            raise ValueError("Oversized response")
        decoded=json.loads(body)
        if not isinstance(decoded,dict):
            raise ValueError("Provider root not an object")
        return decoded
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,
            OSError,ValueError,UnicodeError) as exc:
        # Never claim that a 429/blocked API implies the manga was not found.
        raise HTTPException(
            status_code=503,
            detail="Service de correspondance international indisponible."
        ) from exc


def parse_anilist(payload: dict[str,Any]) -> dict[str,Any]:
    if payload.get("errors") or not isinstance(payload.get("data"),dict):
        raise ValueError("AniList GraphQL errors or absent data")
    page=payload["data"].get("Page")
    if not isinstance(page,dict) or not isinstance(page.get("media"),list):
        raise ValueError("AniList GraphQL media missing")
    entries=page["media"]
    if len(entries)>12:
        raise ValueError("AniList response over the requested limit")
    items=[]
    seen=set()
    for item in entries:
        if not isinstance(item,dict) or item.get("type") != "MANGA":
            continue
        aid=_safe_positive(item.get("id"))
        mal=_safe_positive(item.get("idMal"))
        if not aid or aid in seen:
            continue
        seen.add(aid)
        titles=item.get("title")
        if not isinstance(titles,dict):
            titles={}
        names=[{"language":lang,"title":str(titles[lang]).strip()}
               for lang in ("romaji","english","native")
               if isinstance(titles.get(lang),str) and titles[lang].strip()]
        for synonym in (item.get("synonyms") or [])[:15]:
            if isinstance(synonym,str) and 2<=len(synonym.strip())<=160:
                names.append({"language":"unspecified","title":synonym.strip()})
        items.append({
            "anilist_id":aid,
            "source_mal_id":mal,
            "format":str(item.get("format") or "")[:30],
            "titles":names[:20],
            "source_url":"https://anilist.co/manga/"+str(aid),
            "source_name":"ANILIST",
            "identity_confirmed":False,
        })
    return {"status":"CROSS_ID_CANDIDATES" if items else "NO_CANDIDATES",
            "items":items, "identity_confirmed":False}


def search_anilist(title: str) -> dict[str, Any]:
    term=_query_title(title)
    raw=json.dumps({"query":ANILIST_QUERY,"variables":{"search":term}}).encode("utf-8")
    request=urllib.request.Request(ANILIST_URL,data=raw,headers={
        "Accept":"application/json","Content-Type":"application/json",
        "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; public metadata)",
    },method="POST")
    try:
        return parse_anilist(_read_json(request))
    except ValueError as exc:
        raise HTTPException(status_code=503,
                            detail="Réponse AniList non exploitable.") from exc


def _kitsu_item_ids(payload: dict[str, Any], mal_id: int) -> list[int]:
    rows=payload.get("data")
    if not isinstance(rows,list) or len(rows)>15:
        raise ValueError("Unexpected Kitsu mapping lookup")
    found=set()
    for row in rows:
        if not isinstance(row,dict) or row.get("type") != "mappings":
            continue
        attrs=row.get("attributes") or {}
        if attrs.get("externalSite") != "myanimelist/manga" or (
            _safe_positive(attrs.get("externalId")) != mal_id
        ):
            continue
        relation=(row.get("relationships") or {}).get("item") or {}
        item=relation.get("data") or {}
        if item.get("type") == "manga":
            iid=_safe_positive(item.get("id"))
            if iid:
                found.add(iid)
    return sorted(found)


def _parse_kitsu_mapping(payload: dict[str,Any], expected_mal: int,
                         kitsu_id:int) -> dict[str,Any]:
    rows=payload.get("data")
    if not isinstance(rows,list) or len(rows)>80:
        raise ValueError("Unexpected Kitsu item mappings")
    mal=set()
    ani=set()
    for row in rows:
        if not isinstance(row,dict) or row.get("type")!="mappings":
            continue
        attrs=row.get("attributes") or {}
        extid=_safe_positive(attrs.get("externalId"))
        if extid is None:
            continue
        site=attrs.get("externalSite")
        if site=="myanimelist/manga":
            mal.add(extid)
        elif site=="anilist/manga":
            ani.add(extid)
    if mal != {expected_mal}:
        return {"status":"MAL_ID_CONFLICT_OR_MISSING","kitsu_id":kitsu_id,
                "source_mal_id":expected_mal,
                "observed_mal_ids":sorted(mal),
                "anilist_ids":sorted(ani),
                "identity_confirmed":False}
    if len(ani)>1:
        status="ANILIST_ID_CONFLICT"
    elif ani:
        status="MAL_ANILIST_CROSS_ID_REVIEW"
    else:
        status="MAL_MAPPING_ONLY"
    return {"status":status,"kitsu_id":kitsu_id,
            "source_mal_id":expected_mal,
            "anilist_ids":sorted(ani),
            "source_url":"https://kitsu.app/manga/"+str(kitsu_id),
            "identity_confirmed":False}


def search_kitsu_by_mal(mal_id: int) -> dict[str,Any]:
    mid=_safe_positive(mal_id)
    if not mid:
        raise ValueError("A positive MyAnimeList manga ID is required.")
    params=urllib.parse.urlencode({
        "filter[externalSite]":"myanimelist/manga",
        "filter[externalId]":str(mid),
        "page[limit]":"12",
    })
    request=urllib.request.Request(KITSU_URL+"/mappings?"+params,headers={
        "Accept":"application/vnd.api+json",
        "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; public metadata)",
    })
    ids=_kitsu_item_ids(_read_json(request),mid)
    if not ids:
        return {"status":"NO_KITSU_MAPPING","items":[]}
    if len(ids)>1:
        return {"status":"AMBIGUOUS_KITSU_ITEMS",
                "items":[{"kitsu_id":k,"identity_confirmed":False} for k in ids]}
    kitsu_id=ids[0]
    details=urllib.request.Request(
        KITSU_URL+"/manga/"+str(kitsu_id)+"/mappings",
        headers={"Accept":"application/vnd.api+json",
                 "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; public metadata)"})
    row=_parse_kitsu_mapping(_read_json(details),mid,kitsu_id)
    return {"status":row["status"],"items":[row]}


def combine_cross_id_sources(
    anilist: dict[str,Any], kitsu: list[dict[str,Any]]
) -> dict[str,Any]:
    """Provider correlation: Kitsu is not proof independent of AniList."""
    bymal={}
    for item in anilist.get("items",[]):
        mid=item.get("source_mal_id")
        if mid:
            bymal.setdefault(mid,[]).append(item["anilist_id"])
    conflicts=[]
    agreements=[]
    for result in kitsu:
        for row in result.get("items",[]):
            mid=row.get("source_mal_id")
            claimed=set(row.get("anilist_ids") or [])
            observed=set(bymal.get(mid) or [])
            if row.get("status") in ("MAL_ID_CONFLICT_OR_MISSING",
                                     "ANILIST_ID_CONFLICT") or (
                claimed and observed and claimed != observed
            ):
                conflicts.append({"source_mal_id":mid,"kitsu_id":row.get("kitsu_id"),
                                  "anilist_ids":sorted(observed),
                                  "kitsu_claims":sorted(claimed)})
            elif row.get("status")=="MAL_ANILIST_CROSS_ID_REVIEW" and claimed==observed:
                agreements.append({"source_mal_id":mid,
                                   "anilist_id":sorted(claimed)[0],
                                   "kitsu_id":row["kitsu_id"]})
    status=("CONTRADICTION_REVIEW" if conflicts else
            "CROSS_ID_AGREEMENT_REVIEW" if agreements else
            "NOT_CORROBORATED")
    return {"status":status,"agreements":agreements[:12],
            "contradictions":conflicts[:12],
            "independent_identity_proven":False,
            "ownership_assigned":False}
