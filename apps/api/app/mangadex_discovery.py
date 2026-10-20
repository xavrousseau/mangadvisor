"""Explicit MangaDex public-metadata lookup for pending inventory searches.

MangaDex is optional and noncommercial with attribution. The returned manga
must declare a MyAnimeList *manga* ID in links.mal, which must exist in the
Mangadvisor catalog; otherwise no candidate is returned. No chapters/images.
No persistence or automatic mapping; results are manual suggestions only.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Callable

from fastapi import HTTPException

UUID = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.I)
MAL = re.compile(r"^[1-9][0-9]{0,8}$")
MAX_JSON = 450_000

def search_mangadex(title: str) -> dict[str, Any]:
    term=title.strip()
    if not 2<=len(term)<=100:
        raise ValueError("La recherche MangaDex doit contenir 2 à 100 caractères.")
    url="https://api.mangadex.org/manga?"+urllib.parse.urlencode({
        "title":term,"limit":"12",
        "contentRating[]":"safe",
    })
    req=urllib.request.Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; metadata only)",
    })
    try:
        with urllib.request.urlopen(req,timeout=18) as response:
            data=response.read(MAX_JSON+1)
    except (urllib.error.HTTPError, urllib.error.URLError,OSError,TimeoutError) as exc:
        raise HTTPException(status_code=503,
                            detail="MangaDex indisponible : essaie de nouveau plus tard.") from exc
    if len(data)>MAX_JSON:
        raise HTTPException(status_code=503,detail="Réponse MangaDex trop volumineuse.")
    try:
        result=json.loads(data)
    except (ValueError,UnicodeError) as exc:
        raise HTTPException(status_code=503,detail="Réponse MangaDex invalide.") from exc
    if not isinstance(result,dict) or result.get("result")!="ok" or not isinstance(result.get("data"),list):
        raise HTTPException(status_code=503,detail="Réponse MangaDex incohérente.")
    return result


def extract_mal_candidates(payload: dict[str, Any]) -> dict[int,dict[str,Any]]:
    """A manga lacking an explicit links.mal is NOT a verified candidate."""
    candidates={}
    for row in payload.get("data",[])[:12]:
        if not isinstance(row,dict) or row.get("type")!="manga":
            continue
        external_id=row.get("id")
        if not isinstance(external_id,str) or not UUID.fullmatch(external_id):
            continue
        attributes=row.get("attributes") or {}
        if not isinstance(attributes,dict) or attributes.get("contentRating") not in ("safe",None):
            continue
        linked=attributes.get("links") or {}
        mal=linked.get("mal") if isinstance(linked,dict) else None
        if not isinstance(mal,(str,int)) or not MAL.fullmatch(str(mal)):
            continue
        mal_id=int(mal)
        titles=[]
        main=attributes.get("title")
        alternatives=attributes.get("altTitles")
        for group in ([main] if isinstance(main,dict) else []) + (alternatives[:45] if isinstance(alternatives,list) else []):
            if isinstance(group,dict):
                for lang,value in group.items():
                    if lang in ("fr","en","ja","ja-ro","romaji") and isinstance(value,str) and 2<=len(value.strip())<=200:
                        titles.append({"language_code":lang,"alias":value.strip()})
        if not titles:
            continue
        data={"mangadex_id":external_id,
              "source_url":"https://mangadex.org/title/"+external_id,
              "titles":titles[:40],"source_name":"MANGADEX"}
        # Multiple MangaDex records declaring the same MAL id are ambiguous:
        # do not arbitrarily choose which alias record is correct.
        if mal_id in candidates:
            candidates[mal_id]=None
        else:
            candidates[mal_id]=data
    return {k:v for k,v in candidates.items() if v is not None}


def search_verified_mangadex(
    cur: Any, term: str, lookup: Callable[[str],dict[str,Any]]=search_mangadex
) -> list[dict[str,Any]]:
    candidates=extract_mal_candidates(lookup(term))
    if not candidates:
        return []
    cur.execute("""
        SELECT m.id,m.title,m.title_english,m.title_japanese,
               m.source_mal_id,m.volumes,m.manga_type
        FROM manga m
        WHERE m.source_mal_id=ANY(%(ids)s)
        ORDER BY m.popularity ASC NULLS LAST,m.id
        LIMIT 12
    """,{"ids":list(candidates)})
    results=[]
    for row in cur.fetchall():
        item=candidates.get(int(row["source_mal_id"]))
        if not item:
            continue
        preferred=next((x["alias"] for x in item["titles"]
                        if x["language_code"]=="fr"),item["titles"][0]["alias"])
        results.append({
            **dict(row),
            "matched_alias":preferred,
            "suggestion_kind":"MANGADEX_MAL_LINK",
            "source_name":"MANGADEX",
            "source_url":item["source_url"],
            "verification_basis":"mangadex_links_mal_exact",
        })
    return results
