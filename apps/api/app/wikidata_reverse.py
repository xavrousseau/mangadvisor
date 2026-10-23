"""Optional reverse Wikidata lookup: exact FR/EN label -> P4087 MAL manga ID.

Only metadata; never a user-library, volume, work or ISBN write. An exact
Wikidata label may be wrong: treat returned IDs as inspectable evidence,
not automatic identity truth. The lookup is opt-in and rate bounded.
"""
from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import Any
from fastapi import HTTPException

ENDPOINT="https://query.wikidata.org/sparql"
QID=re.compile(r"^https?://www\.wikidata\.org/entity/(Q[1-9]\d{0,11})$")
MAL=re.compile(r"^[1-9]\d{0,8}$")
MAX_BYTES=300_000
MAX_RESULTS=25


def sparql_exact_title(text: str) -> str:
    clean=text.strip()
    if not 2<=len(clean)<=100 or any(ord(ch)<32 for ch in clean):
        raise ValueError("Invalid Wikidata title query.")
    # JSON escaping is SPARQL-string compatible for quotes/backslashes.
    literal=json.dumps(clean,ensure_ascii=False)
    return (
        "SELECT DISTINCT ?item ?malId WHERE { "
        "{ ?item <http://www.w3.org/2000/01/rdf-schema#label> "+literal+"@fr . } "
        "UNION { ?item <http://www.w3.org/2004/02/skos/core#altLabel> "+literal+"@fr . } "
        "UNION { ?item <http://www.w3.org/2000/01/rdf-schema#label> "+literal+"@en . } "
        "UNION { ?item <http://www.w3.org/2004/02/skos/core#altLabel> "+literal+"@en . } "
        "?item <http://www.wikidata.org/prop/direct/P4087> ?malId . "
        "} LIMIT 26"
    )


def parse_reverse_result(payload: dict[str,Any]) -> dict[str,Any]:
    bindings=payload.get("results",{}).get("bindings")
    if not isinstance(bindings,list):
        raise ValueError("Unexpected Wikidata response.")
    if len(bindings)>MAX_RESULTS:
        return {"status":"TRUNCATED_REVIEW","items":[],"truncated":True}
    found=set()
    for binding in bindings:
        if not isinstance(binding,dict):
            continue
        q=str((binding.get("item") or {}).get("value") or "")
        mal=str((binding.get("malId") or {}).get("value") or "")
        match=QID.fullmatch(q)
        if match and MAL.fullmatch(mal):
            found.add((int(mal),match.group(1)))
    return {
        "status":"EXACT_LABEL_CROSS_ID_CANDIDATES" if found else "NO_CROSS_ID",
        "items":[{"source_mal_id":mid,"wikidata_id":qid,
                  "source_url":"https://www.wikidata.org/wiki/"+qid,
                  "evidence":"WIKIDATA_EXACT_FR_EN_LABEL_WITH_P4087",
                  "work_identity_confirmed":False}
                 for mid,qid in sorted(found)[:MAX_RESULTS]],
        "truncated":False,
    }


def search_wikidata_mal_titles(text: str) -> dict[str,Any]:
    sparql=sparql_exact_title(text)
    url=ENDPOINT+"?"+urllib.parse.urlencode({"query":sparql,"format":"json"})
    request=urllib.request.Request(url,headers={
        "User-Agent":"Mangadvisor/1.0 (https://github.com/xavrousseau/mangadvisor; metadata-only)",
        "Accept":"application/sparql-results+json, application/json",
    })
    try:
        with urllib.request.urlopen(request,timeout=14) as response:
            raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError("Oversized Wikidata reply")
        result=json.loads(raw)
        return parse_reverse_result(result)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,
            OSError,UnicodeError,ValueError) as exc:
        raise HTTPException(status_code=503,detail="Wikidata indisponible pour cette recherche.") from exc
