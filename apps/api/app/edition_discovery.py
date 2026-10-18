"""Candidate-only French bibliographic discovery by TITLE in BnF SRU.

This module NEVER writes manga, editions, user library or reading progress.
An ISBN found in a title-search result is a CANDIDATE, not a verified match
to the selected manga. Registration must pass existing BnF ISBN validation
and explicit manual edition/volume confirmation in the parent collection API.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from apps.api.app.collection import (
    BNF_SOURCE, BNF_SRU, edition_kind_from_title,
    isbn13_normalize, safe_bnf_ark,
)

MAX_BIBLIOGRAPHY_RESULTS = 20
MAX_RESPONSE_BYTES = 1_500_000
SRW = "{http://www.loc.gov/zing/srw/}"
DC = "{http://purl.org/dc/elements/1.1/}"
ISBN_PATTERN = re.compile(r"(?<![0-9])97[89](?:[ -]?[0-9]){10}(?![0-9])")


def sanitize_title_query(title: str) -> str:
    """A single quoted CQL literal. Never accept CQL metacharacters."""
    title = re.sub(r"\s+", " ", title.strip())
    if len(title) < 3 or len(title) > 90:
        raise ValueError("Recherche par titre : saisis entre 3 et 90 caractères.")
    # Unicode letters/numbers, spaces, apostrophes, and simple separators;
    # reject quotation marks, parentheses, backslashes and CQL operators.
    if not all(ch.isalnum() or ch in " -'’.:," for ch in title):
        raise ValueError("Caractères non autorisés dans la recherche.")
    if not any(ch.isalpha() for ch in title):
        raise ValueError("Saisis au moins une lettre dans le titre.")
    return title


def extract_valid_isbns(identifiers: list[str]) -> list[str]:
    """An exact, checksum-validated 13-digit token; no merged identifiers."""
    found: list[str] = []
    for identifier in identifiers:
        for candidate in ISBN_PATTERN.findall(identifier):
            try:
                number = isbn13_normalize(candidate)
            except ValueError:
                continue
            if number not in found:
                found.append(number)
    return found


def parse_title_search_response(raw: bytes, *, limit: int = MAX_BIBLIOGRAPHY_RESULTS) -> dict[str, Any]:
    """SRU 1.2 Dublin Core; strict BnF ARK and valid ISBN per candidate."""
    if len(raw) > MAX_RESPONSE_BYTES or re.search(rb"<!\s*(DOCTYPE|ENTITY)\b",raw,re.I):
        raise ValueError("Réponse XML BnF invalide ou trop volumineuse.")
    root=ET.fromstring(raw)
    total_text=root.findtext(SRW+"numberOfRecords")
    reported_total=int(total_text) if total_text and total_text.isdigit() else None
    results: list[dict[str,Any]]=[]
    seen: set[str]=set()
    checked_at=datetime.now(timezone.utc).isoformat()
    for record in root.findall(".//"+SRW+"record"):
        ark=safe_bnf_ark(record.findtext(SRW+"recordIdentifier") or "")
        if not ark:
            continue
        fields:dict[str,list[str]]={}
        for node in record.findall(".//"+DC+"*"):
            if node.text and node.text.strip():
                key=node.tag.rsplit("}",1)[-1]
                fields.setdefault(key,[]).append(node.text.strip())
        title=next(iter(fields.get("title",[])),"")[:350]
        if not title:
            continue
        isbns=extract_valid_isbns(fields.get("identifier",[]))
        if not isbns:
            continue
        creators=fields.get("creator") or fields.get("contributor") or []
        publishers=fields.get("publisher") or []
        dates=fields.get("date") or []
        languages=fields.get("language") or []
        for isbn in isbns:
            if isbn in seen:
                continue
            seen.add(isbn)
            results.append({
                "isbn13":isbn,
                "title_fr":title,
                "author_fr":"; ".join(creators[:4])[:350] or None,
                "publisher_fr":"; ".join(publishers[:2])[:200] or None,
                "release_date_text":dates[0][:80] if dates else None,
                "language_recorded":languages[0][:60] if languages else None,
                "edition_kind_suggested":edition_kind_from_title(title),
                "source_name":BNF_SOURCE,
                "source_url":"https://catalogue.bnf.fr/"+ark,
                "source_checked_at":checked_at,
                "status":"CANDIDATE_UNCONFIRMED",
                "manga_match_verified":False,
            })
            if len(results)>=limit:
                break
        if len(results)>=limit:
            break
    return {"items":results, "count":len(results),
            "bnf_reported_records":reported_total,
            "search_scope":"first_page_title_search_only",
            "exhaustive":False,
            "candidate_only":True,
            "message":"Notices candidates par titre uniquement. Les ISBN doivent être vérifiés et associés manuellement à la série."}


def search_bnf_by_title(query: str, *, start_record: int = 1) -> dict[str,Any]:
    cleaned=sanitize_title_query(query)
    # Fixed 20-record BnF pages, at most three. Existing manual discovery stays at page 1.
    if start_record not in (1, 21, 41):
        raise ValueError("Page BnF non autorisée.")
    args=urllib.parse.urlencode({
        "version":"1.2","operation":"searchRetrieve",
        "query":f'bib.title all "{cleaned}"',
        "recordSchema":"dublincore",
        "startRecord":start_record,
        "maximumRecords":MAX_BIBLIOGRAPHY_RESULTS,
    })
    request=urllib.request.Request(BNF_SRU+"?"+args,headers={
        "User-Agent":"Mangadvisor-local/1.2 (manual title bibliography candidate search)",
        "Accept":"application/xml",
    })
    try:
        with urllib.request.urlopen(request,timeout=9) as response:
            raw=response.read(MAX_RESPONSE_BYTES+1)
        parsed=parse_title_search_response(raw)
        if start_record != 1:
            parsed["search_scope"]="requested_title_search_page"
        parsed["bnf_start_record"]=start_record
        parsed["bnf_page_size"]=MAX_BIBLIOGRAPHY_RESULTS
        return parsed
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, ET.ParseError) as exc:
        raise HTTPException(status_code=503,detail=
            "La recherche dans le catalogue BnF est momentanément indisponible ; aucune édition n'a été ajoutée.") from exc


def edition_discovery_router(connection_factory: Callable[...,Any]) -> APIRouter:
    router=APIRouter(prefix="/collection",tags=["Recherche bibliographique française"])

    @router.get("/mangas/{manga_id}/discover")
    def discover_book_candidates(manga_id:int,title:str) -> dict[str,Any]:
        try:
            safe=sanitize_title_query(title)
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM manga WHERE id=%(manga_id)s;",{"manga_id":manga_id})
                if not cur.fetchone():
                    raise HTTPException(status_code=404,detail="Manga inconnu.")
        found=search_bnf_by_title(safe)
        return {"manga_id":manga_id,"searched_title":safe,**found}

    return router
