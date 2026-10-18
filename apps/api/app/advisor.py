"""Mangadvisor conversational advisor: bounded, auditable intent-to-SQL retrieval.

This is a guided natural-language interpreter, not an unrestricted LLM. No
unsourced manga facts, fictional French editions, chat persistence or DB writes.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.api.app.mood_discovery import MOODS, match_mood, preference_overlap

router = APIRouter(prefix="/advisor", tags=["Conversational manga advisor"])
Mood = Literal["DARK", "COMFORT", "ACTION", "MYSTERY", "ROMANCE", "FANTASY"]
Length = Literal["ANY", "SHORT", "LONG"]
FrenchEvidence = Literal["ANY", "PREFER", "REQUIRE"]

class AdvisorContext(BaseModel):
    mood: Mood | None = None
    secondary_mood: Mood | None = None
    length: Length = "ANY"
    only_finished: bool | None = None
    french: FrenchEvidence = "ANY"
    use_library: bool = True
    avoid_romance: bool = False
    min_score: float = Field(default=6.5, ge=0, le=10)

class AdvisorRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=500)
    context: AdvisorContext = Field(default_factory=AdvisorContext)
    seen_ids: list[int] = Field(default_factory=list, max_length=100)
    lang: Literal["fr", "en"] = "fr"
    limit: int = Field(default=6, ge=1, le=12)

# Patterns operate on accent-normalized, word-boundary controlled strings.
MOOD_PATTERNS: dict[str, tuple[str, ...]] = {
    "DARK": (r"\bsombre\b",r"\bnoir(?:e)?\b",r"\bdark\b",r"\bhorreur\b",r"\bhorror\b",r"\bgore\b"),
    "MYSTERY": (r"\bmyster",r"\benquete\b",r"\bdetective\b",r"\bpolicier\b",r"\bintrigue\b",r"\bsuspense\b",r"\bthriller\b",r"\bmystery\b"),
    "ACTION": (r"\baction\b",r"\baventure",r"\bcombat",r"\bbaston\b",r"\bepique\b",r"\badventure\b"),
    "COMFORT": (r"\bdoux\b",r"\bmignon",r"\breconfort",r"\bfeel.good\b",r"\bcalme\b",r"\bquotidien\b",r"\bcozy\b",r"\brelax"),
    "ROMANCE": (r"\bromanc",r"\bromantique\b",r"\bamour\b",r"\blove.story\b"),
    "FANTASY": (r"\bfantastique\b",r"\bfantasy\b",r"\bfantaisie\b",r"\bmagie\b",r"\bmagique\b",r"\bimaginaire\b",r"\bheroic"),
}
NEGATION_BEFORE = re.compile(r"(?:pas de|pas d|sans|eviter|evite|no|without|avoid|ni)\s+(?:\w+\s+){0,2}$")
RESET = re.compile(r"\b(recommenc|repartir de zero|nouvelle recherche|reset|start over)\b")
MORE = re.compile(r"\b(autres?|d.autres|encore|more|another|different)\b")
FINISHED = re.compile(r"\b(termin\w*|fini\w*|complet\w*|finished|completed)\b")
UNFINISHED = re.compile(r"\b(en cours de publication|ongoing|publishing|pas termine|non termine)\b")
SHORT = re.compile(r"\b(pas trop long|plutot court|court\w*|petite serie|moins de 1[345] tomes|short|not too long)\b")
LONG = re.compile(r"\b(longue? serie|plutot long|longue?\b|long series?)\b")
FRENCH = re.compile(r"\b(francais|francaise|france|vf\b|french|traduit en francais)\b")
FRENCH_REQUIRED = re.compile(r"\b(obligatoire\w*|uniquement|absolument|imperatif|seulement|must|only|require)\b")
FRENCH_OPTIONAL = re.compile(r"\b(idealement|si possible|de preference|prefer|ideally|preferably)\b")
ROMANCE = re.compile(r"\b(romance|romantique|amour|love.story)\b")
MATURE = re.compile(r"\b(mature|adulte|adultes|seinen)\b")
LIBRARY_OFF = re.compile(r"\b(sans (?:mes |ma )?(?:gouts|bibliotheque|preferences)|sans personnalisation|ignore my library|without my library)\b")
LIBRARY_ON = re.compile(r"\b(selon mes gouts|mes preferences|ma bibliotheque|my library|my taste)\b")
RATING = re.compile(r"\b(?:note|score|rating)\s*(?:minimum|min|de|d.au moins|>=|superieure a)?\s*(\d{1,2}(?:[.,]\d)?)\s*(?:/10)?\b")

def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))

def interpret(message: str, context: AdvisorContext) -> tuple[AdvisorContext, list[str], bool, list[str]]:
    """Merge only explicitly stated constraints, leave the others untouched."""
    normalized = normalize(message).replace("’", "'")
    current = AdvisorContext() if RESET.search(normalized) else context.model_copy(deep=True)
    changes: list[str] = []
    warnings: list[str] = []
    hits: list[tuple[int,str]] = []
    excluded_romance = False
    for mood, patterns in MOOD_PATTERNS.items():
        for pattern in patterns:
            for found in re.finditer(pattern, normalized):
                prefix = normalized[max(0, found.start()-46):found.start()]
                if NEGATION_BEFORE.search(prefix):
                    if mood == "ROMANCE":
                        excluded_romance = True
                    continue
                hits.append((found.start(),mood))
    hits.sort()
    moods = list(dict.fromkeys(mood for _, mood in hits))
    if moods:
        current.mood = moods[0]
        current.secondary_mood = moods[1] if len(moods)>1 else None
        changes.append("mood")
        if current.mood == "ROMANCE":
            current.avoid_romance = False
    if excluded_romance or re.search(r"\b(pas de romance|sans romance|avoid romance|no romance)\b",normalized):
        current.avoid_romance = True
        changes.append("avoid_romance")
        if current.mood == "ROMANCE":
            current.mood = None
        if current.secondary_mood == "ROMANCE":
            current.secondary_mood = None
    if SHORT.search(normalized):
        current.length = "SHORT"; changes.append("length")
    elif LONG.search(normalized):
        current.length = "LONG"; changes.append("length")
    elif re.search(r"\b(peu importe (?:la longueur|le nombre de tomes)|any length)\b",normalized):
        current.length = "ANY"; changes.append("length")
    # A negation about finished series must not be interpreted as "finished".
    if re.search(r"\b(pas forcement termin|pas necessairement termin|any status|peu importe.*termin)\w*",normalized):
        current.only_finished = None;changes.append("only_finished")
    elif UNFINISHED.search(normalized):
        current.only_finished = False;changes.append("only_finished")
    elif FINISHED.search(normalized):
        current.only_finished = True;changes.append("only_finished")
    if FRENCH.search(normalized):
        current.french = "PREFER" if FRENCH_OPTIONAL.search(normalized) else "REQUIRE"
        if FRENCH_REQUIRED.search(normalized):
            current.french = "REQUIRE"
        changes.append("french")
    elif re.search(r"\b(sans contrainte de langue|peu importe la langue|any language)\b",normalized):
        current.french = "ANY";changes.append("french")
    if LIBRARY_OFF.search(normalized):
        current.use_library = False;changes.append("use_library")
    elif LIBRARY_ON.search(normalized):
        current.use_library = True;changes.append("use_library")
    rating = RATING.search(normalized)
    if rating:
        number=float(rating.group(1).replace(",","."))
        if 0<=number<=10:
            current.min_score=number;changes.append("min_score")
    if MATURE.search(normalized):
        warnings.append("maturity_not_verified")
    # Dedicated clarification rather than pretending arbitrary unknown text was parsed.
    return current, list(dict.fromkeys(changes)), bool(MORE.search(normalized)), warnings

def score_candidates(
    rows: list[dict[str, Any]], context: AdvisorContext,
    preferences: dict[str, set[str]], limit: int,
) -> list[dict[str, Any]]:
    selected = []
    mood_list = [x for x in (context.mood,context.secondary_mood) if x]
    for item in rows:
        matches: dict[str,list[str]]={"genres":[],"themes":[]}
        hits = 0
        for mood in mood_list:
            group = match_mood(item,mood)
            if any(group.values()):
                hits+=1
            for key in ("genres","themes"):
                matches[key].extend(x for x in group[key] if x not in matches[key])
        # Every requested mood must have a documented matching tag.
        if hits < len(mood_list):continue
        affinity = preference_overlap(item,preferences)
        verified = int(item.get("french_record_count") or 0)>0
        french_score = 24 if context.french=="PREFER" and verified else 0
        rank = (
            18*len(matches["genres"]) + 21*len(matches["themes"])
            + min(20, 5*len(affinity["genres"])+7*len(affinity["themes"]))
            + french_score + 2*float(item.get("score") or 0)
        )
        selected.append((rank,float(item.get("score") or 0),
                         -int(item.get("popularity") or 99999999),-int(item["id"]),{
            **item,"mood_matches":matches,"affinity_matches":affinity,
            "french_recorded":verified,
            "ranking_score":None,
        }))
    selected.sort(key=lambda row:row[:4],reverse=True)
    return [row[4] for row in selected[:limit]]

def describe_context(context:AdvisorContext,lang:str)->str:
    """Reveal interpreted constraints, not invisible assumptions."""
    fr=lang=="fr"
    labels={
        "DARK":("sombre","dark"),"COMFORT":("douceur","cozy"),
        "ACTION":("action","action"),"MYSTERY":("mystère","mystery"),
        "ROMANCE":("romance","romance"),"FANTASY":("fantastique","fantasy"),
    }
    parts=[labels[mood][0 if fr else 1]
           for mood in (context.mood,context.secondary_mood) if mood]
    if context.length=="SHORT":
        parts.append("12 tomes maximum" if fr else "up to 12 volumes")
    elif context.length=="LONG":
        parts.append("13 tomes et plus" if fr else "13+ volumes")
    if context.only_finished is True:
        parts.append("série terminée" if fr else "finished series")
    elif context.only_finished is False:
        parts.append("série en cours de publication" if fr else "currently publishing")
    if context.french=="REQUIRE":
        parts.append("ISBN français enregistré obligatoire" if fr else "recorded French ISBN required")
    elif context.french=="PREFER":
        parts.append("ISBN français enregistré souhaité" if fr else "recorded French ISBN preferred")
    if context.avoid_romance:
        parts.append("sans romance documentée" if fr else "without tagged romance")
    parts.append(("tes goûts" if fr else "your tastes") if context.use_library
                 else ("sans personnalisation" if fr else "no personalization"))
    return " · ".join(parts)


def make_advisor_router(connection_factory:Callable[...,Any],user_id:int=1)->APIRouter:
    @router.post("/message")
    def ask_advisor(payload:AdvisorRequest)->dict[str,Any]:
        context,changes,more,warnings=interpret(payload.message,payload.context)
        data={"context":context.model_dump(),"changes":changes,
              "limitations":warnings,"recommendations":[],"count":0,"personalized":False}
        is_fr=payload.lang=="fr"
        if context.mood is None:
            data.update(status="clarify",reply=(
                "Quelle ambiance cherches-tu : sombre, mystère, action, romance, fantastique ou douceur ?"
                if is_fr else "What mood: dark, mystery, action, romance, fantasy or cozy?"
            ))
            return data
        # A continuation with no recognized intent should request reformulation.
        if not changes and not more and not RESET.search(normalize(payload.message)):
            data.update(status="clarify",reply=(
                "Je n'ai pas identifié de nouveau critère. Précise une ambiance, la longueur, le statut ou le français."
                if is_fr else "I couldn't identify a new filter. Try a mood, length, publication status or French editions."
            ))
            return data

        moods=[x for x in (context.mood,context.secondary_mood) if x]
        genre_tags=set()
        theme_tags=set()
        for mood in moods:
            genre_tags.update(tag.lower() for tag in MOODS[mood]["genres"])
            theme_tags.update(tag.lower() for tag in MOODS[mood]["themes"])
        params:dict[str,Any]={
            "user_id":user_id,"min_score":context.min_score,
            "genres":sorted(genre_tags),"themes":sorted(theme_tags),
        }
        conditions=[
            "COALESCE(m.manga_type,'Manga') IN ('Manga','Manhwa','Manhua','One-shot')",
            "COALESCE(m.score,0) >= %(min_score)s",
            """NOT EXISTS (SELECT 1 FROM user_manga_library u
               WHERE u.user_id=%(user_id)s AND u.manga_id=m.id)""",
            """NOT EXISTS (SELECT 1 FROM user_manga_volume v
               JOIN manga_fr_edition ee ON ee.id=v.edition_id
               WHERE v.user_id=%(user_id)s AND ee.manga_id=m.id
                 AND (v.is_owned=TRUE OR v.is_read=TRUE))""",
            """(EXISTS (SELECT 1 FROM manga_genre mg JOIN genre g ON g.id=mg.genre_id
               WHERE mg.manga_id=m.id AND LOWER(g.name)=ANY(%(genres)s))
             OR EXISTS (SELECT 1 FROM manga_theme mt JOIN theme t ON t.id=mt.theme_id
               WHERE mt.manga_id=m.id AND LOWER(t.name)=ANY(%(themes)s)))""",
        ]
        if context.only_finished is True:
            conditions.append("LOWER(COALESCE(m.status,''))='finished'")
        if context.only_finished is False:
            conditions.append("LOWER(COALESCE(m.status,''))='publishing'")
        if context.length=="SHORT":
            conditions.append("m.volumes BETWEEN 1 AND 12")
        elif context.length=="LONG":
            conditions.append("m.volumes>=13")
        if context.french=="REQUIRE":
            conditions.append("EXISTS (SELECT 1 FROM manga_fr_edition fe WHERE fe.manga_id=m.id)")
        if context.avoid_romance:
            conditions.append("""NOT EXISTS (SELECT 1 FROM manga_genre rmg
                JOIN genre rg ON rg.id=rmg.genre_id
                WHERE rmg.manga_id=m.id AND LOWER(rg.name)='romance')""")
        if more and payload.seen_ids:
            conditions.append("NOT (m.id=ANY(%(seen_ids)s))")
            params["seen_ids"]=payload.seen_ids
        sql = """
            SELECT m.id,m.title,m.status,m.volumes,m.chapters,m.score::float AS score,
                m.popularity,m.manga_type,
                ARRAY(SELECT g.name FROM manga_genre mg JOIN genre g ON g.id=mg.genre_id
                      WHERE mg.manga_id=m.id ORDER BY g.name) AS genres,
                ARRAY(SELECT t.name FROM manga_theme mt JOIN theme t ON t.id=mt.theme_id
                      WHERE mt.manga_id=m.id ORDER BY t.name) AS themes,
                (SELECT COUNT(*)::int FROM manga_fr_edition fe
                    WHERE fe.manga_id=m.id) AS french_record_count
            FROM manga m WHERE """+" AND ".join(conditions)+"""
            ORDER BY m.score DESC NULLS LAST,m.popularity ASC NULLS LAST,m.id ASC
            LIMIT 500
        """
        preference_sql="""
            WITH positive AS (
                SELECT manga_id FROM user_manga_library
                WHERE user_id=%(user_id)s
                  AND library_status NOT IN ('DROPPED','NOT_INTERESTED')
                  AND (is_favorite=TRUE OR user_score>=7 OR
                       (library_status IN ('READ','READING') AND user_score IS NULL))
            )
            SELECT 'genres' AS kind,LOWER(g.name) AS tag
                FROM positive p JOIN manga_genre mg ON mg.manga_id=p.manga_id
                JOIN genre g ON g.id=mg.genre_id
            UNION
            SELECT 'themes' AS kind,LOWER(t.name) AS tag
                FROM positive p JOIN manga_theme mt ON mt.manga_id=p.manga_id
                JOIN theme t ON t.id=mt.theme_id
        """
        preferences:dict[str,set[str]]={"genres":set(),"themes":set()}
        with connection_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(sql,params)
                candidates=cur.fetchall()
                if context.use_library:
                    cur.execute(preference_sql,{"user_id":user_id})
                    for row in cur.fetchall():
                        preferences[row["kind"]].add(row["tag"])
        chosen=score_candidates(candidates,context,preferences,payload.limit)
        personalized=context.use_library and any(preferences.values())
        interpretation=describe_context(context,payload.lang)
        data["interpreted_criteria"]=interpretation
        data.update(
            status="results" if chosen else "empty",
            recommendations=chosen,count=len(chosen),
            personalized=personalized,
            reply=(
                ("J'ai compris : "+interpretation+". Voici des pistes appuyées sur les genres et thèmes du catalogue. "
                 "Les ISBN français ne prouvent pas la disponibilité en magasin."
                 if is_fr else
                 "I understood: "+interpretation+". These picks are grounded in cataloged genres and themes. "
                 "Recorded French ISBNs do not confirm store availability.")
                if chosen else
                ("J'ai compris : "+interpretation+". Aucun titre documenté ne réunit ces critères. Essaie d'assouplir la longueur, la langue ou l'ambiance."
                 if is_fr else
                 "I understood: "+interpretation+". No supported catalog titles meet all conditions. Try relaxing length, French records or mood.")
            ),
        )
        return data
    return router
