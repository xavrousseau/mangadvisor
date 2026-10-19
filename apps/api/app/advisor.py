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
from apps.api.app.narrative_evidence import narrative_matches
from apps.api.app.advisor_editions import fetch_recommended_editions

router = APIRouter(prefix="/advisor", tags=["Conversational manga advisor"])
Mood = Literal["DARK", "COMFORT", "ACTION", "MYSTERY", "ROMANCE", "FANTASY"]
Length = Literal["ANY", "SHORT", "LONG"]
FrenchEvidence = Literal["ANY", "PREFER", "REQUIRE"]
EditionKind = Literal["CLASSIC","DELUXE","PERFECT","COLLECTOR","INTEGRAL","OTHER"]
DiscoveryBalance = Literal["CLOSE", "BALANCED", "EXPLORE"]

class AdvisorContext(BaseModel):
    mood: Mood | None = None
    secondary_mood: Mood | None = None
    length: Length = "ANY"
    only_finished: bool | None = None
    french: FrenchEvidence = "ANY"
    preferred_edition_kind: EditionKind | None = None
    require_edition_kind: bool = False
    use_library: bool = True
    recommendation_balance: DiscoveryBalance = "BALANCED"
    profile_discovery: bool = False  # user-requested library-first discovery without mood
    avoid_romance: bool = False
    avoid_horror: bool = False
    avoid_gore: bool = False
    narrative_preferences: list[Literal["INVESTIGATION","PSYCHOLOGICAL","SURVIVAL"]] = Field(
        default_factory=list, max_length=3
    )
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
RESET = re.compile(r"\b(recommenc\w*|repartir de zero|nouvelle recherche|reset|start over)\b")
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
NARRATIVE_REQUESTS = {
    "INVESTIGATION": (r"\benquet\w*\b", r"\binvestigat\w*\b", r"\bdetectiv\w*\b"),
    "PSYCHOLOGICAL": (r"\bpsycholog\w*\b",),
    "SURVIVAL": (r"\bsurvi\w*\b", r"\bsurviv\w*\b", r"\bsurvival\b"),
}
HORROR_EXCLUDE = re.compile(r"\b(?:sans|pas de|ni|no|without|avoid|eviter|evite)\s+(?:(?:l|la|the)\s+)?(?:horreur|horror)\b")
GORE_EXCLUDE = re.compile(r"\b(?:sans|pas de|ni|no|without|avoid|eviter|evite)\s+(?:(?:le|the)\s+)?gore\b")
HORROR_ALLOW = re.compile(r"\b(?:avec|j.accepte|autorise|allow)\s+(?:(?:l|la|the)\s+)?(?:horreur|horror)\b|\b(?:horreur|horror)\s+(?:ok|me va|is fine)\b")
GORE_ALLOW = re.compile(r"\b(?:avec|autorise|allow)\s+(?:le\s+)?gore\b|\bgore\s+(?:ok|me va|is fine)\b")
LIBRARY_OFF = re.compile(r"\b(sans (?:mes |ma )?(?:gouts|bibliotheque|preferences)|sans personnalisation|ignore my library|without my library)\b")
LIBRARY_ON = re.compile(r"\b(selon mes gouts|mes preferences|ma bibliotheque|my library|my taste)\b")
EDITION_KIND_WORDS = (
    ("DELUXE", r"\bdeluxe\b"),
    ("PERFECT", r"\b(?:perfect|kanzenban)\b"),
    ("COLLECTOR", r"\bcollectors?\b"),
    ("INTEGRAL", r"\b(?:integrale|integral)\b"),
    ("CLASSIC", r"\b(?:classique|classical|standard edition)\b"),
)
EDITION_CLEAR = re.compile(r"\b(?:peu importe (?:l[' ]|le |la )?(?:edition|format)|tout format|any edition|any format)\b")
EDITION_REQUIRED = re.compile(r"\b(?:obligatoire|uniquement|seulement|absolument|only|must|required)\b")
EDITION_PREFERRED = re.compile(r"\b(?:idealement|si possible|de preference|prefer|ideally|preferably)\b")
BALANCE_EXPLORE = re.compile(
    r"\b(surprend\w*|surprise me|surprising|decouvertes?\b|inattendu\w*|"
    r"hors des sentiers battus|unexpected|something different)\b"
)
BALANCE_CLOSE = re.compile(
    r"\b(tres proche\w* de mes gouts|proche\w* de mes gouts|"
    r"meme style|dans le meme style|similar to my tastes|close to my tastes)\b"
)
BALANCE_BALANCED = re.compile(
    r"\b(varie\w*|equilibre\w*|balanced|variety|diversifi\w*)\b"
)
# Profile-first surprise is an explicit opt-in, never a random catalog guess.
PROFILE_DISCOVERY = re.compile(
    r"\b(surprend\w*|surprise me|recommande.moi|recommend me|"
    r"selon mes gouts|according to my taste|based on my tastes)\b"
)
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
        current.profile_discovery = False
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
    if HORROR_EXCLUDE.search(normalized):
        current.avoid_horror=True;changes.append("avoid_horror")
    elif HORROR_ALLOW.search(normalized):
        current.avoid_horror=False;changes.append("avoid_horror")
    if GORE_EXCLUDE.search(normalized):
        current.avoid_gore=True;changes.append("avoid_gore")
    elif GORE_ALLOW.search(normalized):
        current.avoid_gore=False;changes.append("avoid_gore")
    for concept, patterns in NARRATIVE_REQUESTS.items():
        found_positive=False
        for pattern in patterns:
            for occurrence in re.finditer(pattern, normalized):
                prefix=normalized[max(0,occurrence.start()-46):occurrence.start()]
                if not NEGATION_BEFORE.search(prefix):
                    found_positive=True
                    break
            if found_positive:
                break
        if found_positive and concept not in current.narrative_preferences:
            current.narrative_preferences.append(concept)
            changes.append("narrative_preferences")
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
    if EDITION_CLEAR.search(normalized):
        current.preferred_edition_kind=None
        current.require_edition_kind=False
        changes.append("preferred_edition_kind")
    else:
        for kind, pattern in EDITION_KIND_WORDS:
            if re.search(pattern, normalized):
                current.preferred_edition_kind=kind
                current.require_edition_kind=bool(
                    EDITION_REQUIRED.search(normalized)
                    and not EDITION_PREFERRED.search(normalized)
                )
                changes.append("preferred_edition_kind")
                break
    # A discovery balance changes selection variety only, never user filters.
    if BALANCE_EXPLORE.search(normalized):
        current.recommendation_balance = "EXPLORE"
        changes.append("recommendation_balance")
    elif BALANCE_CLOSE.search(normalized):
        current.recommendation_balance = "CLOSE"
        changes.append("recommendation_balance")
    elif BALANCE_BALANCED.search(normalized):
        current.recommendation_balance = "BALANCED"
        changes.append("recommendation_balance")
    if PROFILE_DISCOVERY.search(normalized) and current.mood is None:
        current.profile_discovery = True
        changes.append("profile_discovery")
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

def _tag_keys(item: dict[str, Any]) -> set[str]:
    """Namespaced *recorded* catalog tags for comparing different suggestions."""
    return {
        kind + ":" + str(tag).casefold()
        for kind in ("genres", "themes")
        for tag in (item.get(kind) or [])
        if isinstance(tag, str) and tag
    }


def select_balanced_candidates(
    ranked: list[tuple[float, float, int, int, dict[str, Any]]],
    balance: DiscoveryBalance,
    limit: int,
) -> list[dict[str, Any]]:
    """Re-rank verified eligible candidates, never generate new recommendations.

    CLOSE preserves the original relevance order; BALANCED and EXPLORE
    increasingly penalize repeated catalog tags. A relevance floor prevents
    surprise mode promoting very weak matches over substantially better ones.
    All SQL conditions, exclusions and explicit mood matches are upstream.
    """
    if not ranked or limit <= 0:
        return []
    ranked.sort(key=lambda record: record[:4], reverse=True)
    if balance == "CLOSE":
        return [{**row[4], "variety_evidence": []} for row in ranked[:limit]]

    relevance_floor = max(0.0, ranked[0][0] * (0.75 if balance == "EXPLORE" else 0.85))
    near = [r for r in ranked if r[0] >= relevance_floor]
    remainder = [r for r in ranked if r[0] < relevance_floor]
    penalty = 30 if balance == "EXPLORE" else 12
    picked: list[dict[str, Any]] = []
    already: set[str] = set()
    previous_tags: list[set[str]] = []
    # Work from a bounded SQL candidate pool (500), with a deterministic tie break.
    for pool in (near, remainder):
        remaining = list(pool)
        while remaining and len(picked) < limit:
            selected_index = 0
            selected_key: tuple[float, float, int, int, int] | None = None
            for i, row in enumerate(remaining):
                tags = _tag_keys(row[4])
                overlap = max(
                    (len(tags & earlier) / len(tags | earlier)
                     for earlier in previous_tags if tags | earlier),
                    default=0.0,
                )
                adjusted = row[0] - penalty * overlap
                # Original order is the deterministic tie-breaker.
                key = (adjusted, row[1], row[2], row[3], -i)
                if selected_key is None or key > selected_key:
                    selected_index, selected_key = i, key
            row = remaining.pop(selected_index)
            item = row[4]
            tags = _tag_keys(item)
            # These labels come only from existing source tags absent in earlier picks.
            novel = [
                label for kind in ("genres", "themes")
                for label in (item.get(kind) or [])
                if isinstance(label, str) and kind + ":" + label.casefold() not in already
            ] if picked else []
            picked.append({**item, "variety_evidence": list(dict.fromkeys(novel))[:3]})
            previous_tags.append(tags)
            already.update(tags)
        if len(picked) >= limit:
            break
    return picked


def score_candidates(
    rows: list[dict[str, Any]], context: AdvisorContext,
    preferences: dict[str, set[str]], limit: int,
) -> list[dict[str, Any]]:
    selected = []
    mood_list = [x for x in (context.mood,context.secondary_mood) if x]
    for item in rows:
        tags={str(tag).casefold() for kind in ("genres","themes")
              for tag in (item.get(kind) or [])}
        if context.avoid_horror and "horror" in tags:
            continue
        if context.avoid_gore and "gore" in tags:
            continue
        if context.avoid_romance and "romance" in tags:
            continue
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
        preferred_format=bool(
            context.preferred_edition_kind and item.get("preferred_format_record_count",0)
        )
        format_score = 28 if preferred_format and not context.require_edition_kind else 0
        story_evidence=narrative_matches(item,context.narrative_preferences)
        story_bonus=sum(16 if record["source"]=="catalog_tag" else 9
                        for record in story_evidence)
        rank = (
            18*len(matches["genres"]) + 21*len(matches["themes"])
            + min(20, 5*len(affinity["genres"])+7*len(affinity["themes"]))
            + french_score + format_score + story_bonus + 2*float(item.get("score") or 0)
        )
        selected.append((rank,float(item.get("score") or 0),
                         -int(item.get("popularity") or 99999999),-int(item["id"]),{
            **{k:v for k,v in item.items() if k!="synopsis"},
            "mood_matches":matches,"affinity_matches":affinity,
            "narrative_matches":story_evidence,
            "narrative_unverified":[concept for concept in context.narrative_preferences
                                    if not any(e["concept"]==concept for e in story_evidence)],
            "french_recorded":verified,
            "preferred_format_recorded":preferred_format,
            "ranking_score":None,
        }))
    return select_balanced_candidates(selected, context.recommendation_balance, limit)

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
    if context.profile_discovery and context.mood is None:
        parts.append("selon tes lectures documentées" if fr
                     else "from your recorded readings")
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
    if context.preferred_edition_kind:
        kind=context.preferred_edition_kind
        parts.append(
            ("format français "+kind+(" obligatoire" if context.require_edition_kind else " souhaité"))
            if fr else
            ("French "+kind+" edition "+("required" if context.require_edition_kind else "preferred"))
        )
    balance_labels = {
        "CLOSE": ("proche de tes goûts", "close to your tastes"),
        "BALANCED": ("sélection équilibrée", "balanced picks"),
        "EXPLORE": ("découvertes variées", "exploratory picks"),
    }
    parts.append(balance_labels[context.recommendation_balance][0 if fr else 1])
    if context.avoid_romance:
        parts.append("sans romance documentée" if fr else "without tagged romance")
    if context.avoid_horror:
        parts.append("sans horreur documentée" if fr else "without tagged horror")
    if context.avoid_gore:
        parts.append("sans gore documenté" if fr else "without tagged gore")
    narrative_labels={
        "INVESTIGATION":("enquête","investigation"),
        "PSYCHOLOGICAL":("psychologique","psychological"),
        "SURVIVAL":("survie","survival"),
    }
    if context.narrative_preferences:
        names=[narrative_labels[key][0 if fr else 1] for key in context.narrative_preferences]
        parts.append(("indices narratifs souhaités : " if fr else "preferred narrative clues: ")
                     +", ".join(names))
    parts.append(("tes goûts" if fr else "your tastes") if context.use_library
                 else ("sans personnalisation" if fr else "no personalization"))
    return " · ".join(parts)


def make_advisor_router(connection_factory:Callable[...,Any],user_id:int=1)->APIRouter:
    # Lazy import: advisor_ai imports AdvisorContext but cannot write SQL or manga.
    from apps.api.app.advisor_ai import (
        LocalAiUnavailable, ai_status, interpret_with_ollama, local_ai_enabled,
    )

    @router.get("/ai-status")
    def get_ai_status()->dict[str,Any]:
        return ai_status()

    @router.post("/message")
    def ask_advisor(payload:AdvisorRequest)->dict[str,Any]:
        context,changes,more,warnings=interpret(payload.message,payload.context)
        result=resolve_advisor(payload,context,changes,more,warnings)
        result["ai_mode"]="guided"
        return result

    @router.post("/ai-message")
    def ask_ai_advisor(payload:AdvisorRequest)->dict[str,Any]:
        """Optional local model only parses intent; the same SQL engine retrieves results."""
        ai_requested=local_ai_enabled()
        if ai_requested:
            try:
                context,changes,more=interpret_with_ollama(
                    payload.message,payload.context,payload.lang
                )
                # Explicit caveats are kept by the audited lexical interpreter.
                _,_,_,warnings=interpret(payload.message,payload.context)
                result=resolve_advisor(payload,context,changes,more,warnings)
                result["ai_mode"]="local_ai"
                return result
            except LocalAiUnavailable:
                pass  # Recover reliably without changing collection or returning fake results.
        result=ask_advisor(payload)
        result["ai_mode"]="guided_fallback" if ai_requested else "guided"
        if ai_requested:
            result["ai_notice"]=(
                "IA locale indisponible : conseiller guidé utilisé."
                if payload.lang=="fr" else
                "Local AI unavailable: guided advisor used."
            )
        return result

    def resolve_advisor(
        payload:AdvisorRequest,context:AdvisorContext,
        changes:list[str],more:bool,warnings:list[str],
    )->dict[str,Any]:
        """Only this audited code chooses and explains manga from PostgreSQL."""
        # The local LLM cannot set profile_discovery directly. The server
        # recognizes this explicit intent and then retrieves real library tags.
        if context.mood is None and PROFILE_DISCOVERY.search(normalize(payload.message)):
            context.profile_discovery = True
            if "profile_discovery" not in changes:
                changes = [*changes, "profile_discovery"]
        if context.mood is not None:
            context.profile_discovery = False
        profile_only = context.mood is None and context.profile_discovery and context.use_library
        data={"context":context.model_dump(),"changes":changes,
              "limitations":warnings,"recommendations":[],"count":0,"personalized":False}
        is_fr=payload.lang=="fr"
        if context.mood is None and not profile_only:
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
            "preferred_kind":context.preferred_edition_kind,
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
        ]
        # In mood-first mode tags come from the explicit mood. In library-first
        # mode the same clause is populated with VERIFIED positive-library tags.
        tag_condition = """(EXISTS (SELECT 1 FROM manga_genre mg JOIN genre g ON g.id=mg.genre_id
               WHERE mg.manga_id=m.id AND LOWER(g.name)=ANY(%(genres)s))
             OR EXISTS (SELECT 1 FROM manga_theme mt JOIN theme t ON t.id=mt.theme_id
               WHERE mt.manga_id=m.id AND LOWER(t.name)=ANY(%(themes)s)))"""
        conditions.append(tag_condition)
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
        if context.require_edition_kind and context.preferred_edition_kind:
            conditions.append("""EXISTS (
                SELECT 1 FROM manga_fr_edition ef
                WHERE ef.manga_id=m.id AND ef.edition_kind=%(preferred_kind)s
            )""")
        if context.avoid_romance or context.avoid_horror or context.avoid_gore:
            excluded=[]
            if context.avoid_romance: excluded.append("romance")
            if context.avoid_horror: excluded.append("horror")
            if context.avoid_gore: excluded.append("gore")
            params["excluded_tags"]=excluded
            conditions.append("""NOT EXISTS (SELECT 1 FROM manga_genre eg
                JOIN genre gex ON gex.id=eg.genre_id
                WHERE eg.manga_id=m.id AND LOWER(gex.name)=ANY(%(excluded_tags)s))""")
            conditions.append("""NOT EXISTS (SELECT 1 FROM manga_theme et
                JOIN theme tex ON tex.id=et.theme_id
                WHERE et.manga_id=m.id AND LOWER(tex.name)=ANY(%(excluded_tags)s))""")
        if more and payload.seen_ids:
            conditions.append("NOT (m.id=ANY(%(seen_ids)s))")
            params["seen_ids"]=payload.seen_ids
        sql = """
            SELECT m.id,m.title,m.status,m.volumes,m.chapters,m.synopsis,m.score::float AS score,
                m.popularity,m.manga_type,
                ARRAY(SELECT g.name FROM manga_genre mg JOIN genre g ON g.id=mg.genre_id
                      WHERE mg.manga_id=m.id ORDER BY g.name) AS genres,
                ARRAY(SELECT t.name FROM manga_theme mt JOIN theme t ON t.id=mt.theme_id
                      WHERE mt.manga_id=m.id ORDER BY t.name) AS themes,
                (SELECT COUNT(*)::int FROM manga_fr_edition fe
                    WHERE fe.manga_id=m.id) AS french_record_count,
                (SELECT COUNT(*)::int FROM manga_fr_edition fkind
                    WHERE fkind.manga_id=m.id AND
                          fkind.edition_kind=%(preferred_kind)s) AS preferred_format_record_count
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
                # Read personal evidence before candidate SQL; in profile-only
                # mode the tags become bounded SQL filters, never model output.
                if context.use_library:
                    cur.execute(preference_sql,{"user_id":user_id})
                    for row in cur.fetchall():
                        preferences[row["kind"]].add(row["tag"])
                if profile_only:
                    if not any(preferences.values()):
                        data.update(status="clarify",reply=(
                            "Je n'ai pas encore assez de lectures favorites ou bien notées pour te surprendre. "
                            "Ajoute quelques lectures ou choisis une ambiance."
                            if is_fr else
                            "I need a few favorite or highly-rated readings first. "
                            "Add some manga to your library or choose a mood."
                        ))
                        return data
                    params["genres"]=sorted(preferences["genres"])
                    params["themes"]=sorted(preferences["themes"])
                cur.execute(sql,params)
                candidates=cur.fetchall()
        chosen=score_candidates(candidates,context,preferences,payload.limit)
        edition_summaries=fetch_recommended_editions(
            connection_factory,[row["id"] for row in chosen]
        ) if chosen else {}
        for row in chosen:
            row["french_editions"]=edition_summaries.get(row["id"])
        personalized=context.use_library and any(preferences.values())
        interpretation=describe_context(context,payload.lang)
        data["interpreted_criteria"]=interpretation
        data["discovery_source"]="library_tags" if profile_only else "requested_mood"
        data.update(
            status="results" if chosen else "empty",
            recommendations=chosen,count=len(chosen),
            personalized=personalized,
            reply=(
                (("Je me base sur les genres et thèmes de tes lectures favorites ou bien notées pour te surprendre. "
                   "Les suggestions restent issues du catalogue ; un ISBN n'est pas une preuve de stock."
                   if is_fr else
                   "I used genres and themes from your favorite or highly-rated readings. "
                   "Every pick comes from the catalog; an ISBN doesn't confirm stock.")
                  if profile_only else
                 ("J'ai compris : "+interpretation+". Voici des pistes appuyées sur les genres, thèmes et indices textuels réellement trouvés. "
                  "Les ISBN français ne prouvent pas la disponibilité en magasin."
                  if is_fr else
                  "I understood: "+interpretation+". These picks use actual catalog tags and literal synopsis clues. "
                  "Recorded French ISBNs do not confirm store availability."))
                if chosen else
                ("J'ai compris : "+interpretation+". Aucun titre documenté ne réunit ces critères. Essaie d'assouplir la longueur, la langue ou l'ambiance."
                 if is_fr else
                 "I understood: "+interpretation+". No supported catalog titles meet all conditions. Try relaxing length, French records or mood.")
            ),
        )
        return data
    return router
