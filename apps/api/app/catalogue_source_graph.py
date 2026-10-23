"""Public multi-source work graph: independent work identity and attributed claims.

A MyAnimeList manga ID is ONE possible external identity, not the primary key.
An anthology's raw 'title_synonyms' is search/discovery evidence only.
No personal-library tables are read or changed here.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalogue_work (
  id BIGSERIAL PRIMARY KEY,
  legacy_manga_id INTEGER UNIQUE REFERENCES manga(id) ON DELETE RESTRICT,
  origin_source TEXT NOT NULL,
  origin_id TEXT NOT NULL,
  canonical_title TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(origin_source, origin_id),
  CHECK (length(btrim(canonical_title)) BETWEEN 1 AND 500),
  CHECK (length(origin_id) BETWEEN 1 AND 150)
);
-- Critical: source graph scans 228k aliases against 85k canonical titles.
-- Both lookups must be indexed to avoid quadratic rescans.
CREATE INDEX IF NOT EXISTS catalogue_legacy_canonical_key_idx
 ON manga((lower(btrim(title))));
CREATE INDEX IF NOT EXISTS catalogue_work_title_key_idx
 ON catalogue_work((lower(btrim(canonical_title))));
CREATE TABLE IF NOT EXISTS catalogue_work_identifier (
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  media_type TEXT NOT NULL DEFAULT 'manga',
  external_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  evidence_url TEXT NOT NULL,
  identity_status TEXT NOT NULL DEFAULT 'SOURCE_CLAIM'
    CHECK (identity_status IN ('SOURCE_CLAIM','COLLISION_REVIEW','REJECTED','VERIFIED')),
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(work_id,provider,media_type,external_id,source_name)
);
CREATE INDEX IF NOT EXISTS catalogue_identifier_lookup_idx
 ON catalogue_work_identifier(provider,media_type,external_id);
CREATE TABLE IF NOT EXISTS catalogue_title_claim (
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  source_id TEXT NOT NULL,
  language_code TEXT NOT NULL DEFAULT 'und',
  title TEXT NOT NULL,
  title_key TEXT NOT NULL,
  claim_kind TEXT NOT NULL
    CHECK (claim_kind IN ('CANONICAL','TYPED_TITLE','UNVERIFIED_SYNONYM',
                         'EXTERNAL_TITLE')),
  evidence_status TEXT NOT NULL
    CHECK (evidence_status IN ('CANONICAL','SOURCE_LINKED','DISCOVERY_ONLY',
                              'COLLISION_REVIEW','REJECTED','VERIFIED')),
  evidence_url TEXT NOT NULL DEFAULT '',
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(work_id,source_name,language_code,claim_kind,title_key),
  CHECK (length(title) BETWEEN 1 AND 500)
);
CREATE INDEX IF NOT EXISTS catalogue_title_claim_lookup_idx
 ON catalogue_title_claim(title_key,evidence_status);
CREATE TABLE IF NOT EXISTS catalogue_book_claim (
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  isbn13 VARCHAR(13) NOT NULL CHECK (isbn13 ~ '^[0-9]{13}
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  source_work_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  target_provider TEXT NOT NULL,
  target_external_id TEXT NOT NULL,
  target_media_type TEXT NOT NULL DEFAULT 'manga',
  evidence_url TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(work_id,source_name,relation_type,target_provider,target_external_id)
);
"""

# Rebuild from Jikan/MAL identity + current alias data, WITHOUT deleting raw
# evidence, existing manga rows or previously quarantined claims.
BASE_BACKFILL = """
INSERT INTO catalogue_work(legacy_manga_id,origin_source,origin_id,canonical_title)
SELECT m.id,'MAL',m.source_mal_id::text,m.title FROM manga m
ON CONFLICT(origin_source,origin_id) DO UPDATE
 SET canonical_title=EXCLUDED.canonical_title,updated_at=now()
 WHERE catalogue_work.canonical_title IS DISTINCT FROM EXCLUDED.canonical_title;

INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
SELECT w.id,'MAL','manga',m.source_mal_id::text,'JIKAN_MAL',
       'https://myanimelist.net/manga/'||m.source_mal_id,'VERIFIED'
FROM catalogue_work w JOIN manga m ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;

INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
SELECT w.id,'JIKAN_MAL',m.source_mal_id::text,'und',
       left(m.title,500),lower(btrim(left(m.title,500))),
       'CANONICAL','CANONICAL','https://myanimelist.net/manga/'||m.source_mal_id
FROM catalogue_work w JOIN manga m ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;

INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
SELECT w.id,a.source_name,a.source_id,a.language_code,a.alias,a.alias_key,
  CASE WHEN a.source_name='TENRAI_MAL' THEN 'UNVERIFIED_SYNONYM'
       WHEN a.source_name='TENRAI_MAL_TYPED' THEN 'TYPED_TITLE'
       ELSE 'EXTERNAL_TITLE' END,
  CASE
    -- Conflict with ANY other canonical work title: never auto-accept.
    WHEN EXISTS (
      SELECT 1 FROM manga other WHERE other.id <> w.legacy_manga_id
       AND lower(btrim(other.title))=lower(btrim(a.alias))
    ) THEN 'COLLISION_REVIEW'
    -- Jikan's untyped synonyms can be chapter titles / anthology entries.
    WHEN a.source_name='TENRAI_MAL' THEN 'DISCOVERY_ONLY'
    -- Typed and cross-ID-source names are attributed CLAIMS, not verified work.
    ELSE 'SOURCE_LINKED'
  END,
  a.source_url
FROM manga_title_alias a
JOIN catalogue_work w ON w.legacy_manga_id=a.manga_id
WHERE length(btrim(a.alias)) BETWEEN 1 AND 500
ON CONFLICT(work_id,source_name,language_code,claim_kind,title_key)
DO UPDATE SET
  title=EXCLUDED.title,
  source_id=EXCLUDED.source_id,
  evidence_url=EXCLUDED.evidence_url,
  evidence_status=CASE
    WHEN catalogue_title_claim.evidence_status IN ('REJECTED','VERIFIED')
      THEN catalogue_title_claim.evidence_status
    ELSE EXCLUDED.evidence_status END;

INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
SELECT w.id,'WIKIDATA','manga',f.wikidata_id,'WIKIDATA_P4087',
       'https://www.wikidata.org/wiki/'||f.wikidata_id,'SOURCE_CLAIM'
FROM manga_wikidata_fact f
JOIN manga m ON m.id=f.manga_id AND m.source_mal_id=f.source_mal_id
JOIN catalogue_work w ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;

-- Raw BnF notices remain CANDIDATE BOOKS, never confirmed editions.
INSERT INTO catalogue_book_claim
(work_id,isbn13,source_name,source_url,title_fr,author_fr,
 publisher_fr,language_recorded,evidence_status)
SELECT w.id,b.isbn13,b.source_name,b.source_url,b.title_fr,
       b.author_fr,b.publisher_fr,b.language_recorded,
       CASE WHEN EXISTS (
         SELECT 1 FROM manga_bnf_candidate other
         WHERE other.isbn13=b.isbn13 AND other.manga_id<>b.manga_id
       ) THEN 'MULTI_WORK_ISBN_REVIEW'
       ELSE 'BIBLIOGRAPHIC_CANDIDATE' END
FROM manga_bnf_candidate b
JOIN catalogue_work w ON w.legacy_manga_id=b.manga_id
ON CONFLICT(work_id,isbn13,source_name) DO UPDATE SET
  title_fr=EXCLUDED.title_fr,
  author_fr=EXCLUDED.author_fr,
  publisher_fr=EXCLUDED.publisher_fr,
  language_recorded=EXCLUDED.language_recorded,
  source_url=EXCLUDED.source_url,
  evidence_status=CASE
    WHEN catalogue_book_claim.evidence_status IN ('REJECTED','VERIFIED')
      THEN catalogue_book_claim.evidence_status
    ELSE EXCLUDED.evidence_status END;
"""

# Exact identifiers may identify the SAME work across sources, but imported
# community IDs are source claims pending cross-check, not automatic merges.
ID_CLAIM_SQL = """
INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
VALUES (%(work_id)s,%(provider)s,'manga',%(external_id)s,
        %(source_name)s,%(evidence_url)s,'SOURCE_CLAIM')
ON CONFLICT DO NOTHING
"""
IDENTITY_COLLISIONS_SQL = """
UPDATE catalogue_work_identifier ident SET identity_status='COLLISION_REVIEW'
WHERE ident.identity_status <> 'REJECTED'
  AND EXISTS (
    SELECT 1 FROM catalogue_work_identifier other
    WHERE other.provider=ident.provider AND other.media_type=ident.media_type
      AND other.external_id=ident.external_id AND other.work_id<>ident.work_id
  )
"""
TITLE_CLAIM_SQL = """
INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
VALUES (%(work_id)s,%(source_name)s,%(source_id)s,%(language_code)s,
        %(title)s,%(title_key)s,'EXTERNAL_TITLE','SOURCE_LINKED',
        %(evidence_url)s)
ON CONFLICT DO NOTHING
"""
RELATION_CLAIM_SQL = """
INSERT INTO catalogue_work_relation
(work_id,source_name,source_work_id,relation_type,target_provider,
 target_external_id,target_media_type,evidence_url)
VALUES (%(work_id)s,%(source_name)s,%(source_work_id)s,%(relation_type)s,
        %(target_provider)s,%(target_external_id)s,%(target_media_type)s,
        %(evidence_url)s)
ON CONFLICT DO NOTHING
"""

SOURCES = frozenset({"ANILIST","KITSU","MANGADEX","WIKIDATA"})
LANGUAGES = {"romaji":"ja-ro","english":"en","native":"ja",
             "en":"en","fr":"fr","ja":"ja","ja-ro":"ja-ro"}


def title_key(title: str) -> str:
    t=unicodedata.normalize("NFKC",str(title or "")).casefold()
    return " ".join(t.split())[:500]


def checked_int(value: Any) -> int | None:
    if type(value) not in (int,str):
        return None
    text=str(value)
    return int(text) if re.fullmatch(r"[1-9][0-9]{0,9}",text) else None


def ensure_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)


def rebuild_legacy_sources(conn: Any) -> None:
    """Idempotent, source-preserving rebuild. Caller chooses commit/rollback."""
    with conn.cursor() as cur:
        cur.execute(BASE_BACKFILL)
        cur.execute(IDENTITY_COLLISIONS_SQL)


def register_non_mal_work(conn: Any, title: str, *,
                          source: str, external_id: str) -> int:
    """Allow French-native works (e.g. Radiant) without a fake MAL ID."""
    if source not in ("BNF","WIKIDATA","PUBLISHER"):
        raise ValueError("A documented primary source is required.")
    if not title.strip() or not external_id or len(external_id)>150:
        raise ValueError("A verifiable bibliographic source reference is required.")
    with conn.cursor() as cur:
        cur.execute("""
           INSERT INTO catalogue_work
             (legacy_manga_id,origin_source,origin_id,canonical_title)
           VALUES(NULL,%s,%s,%s)
           ON CONFLICT(origin_source,origin_id) DO UPDATE
           SET canonical_title=EXCLUDED.canonical_title
           RETURNING id
        """,(source,external_id,title.strip()))
        return int(cur.fetchone()["id"])


def stage_external_facts(conn: Any, mal_id: int, *,
                         provider: str, source_id: str,
                         url: str, titles: list[dict[str,str]] | None = None,
                         relations: list[dict[str,Any]] | None = None) -> dict:
    """Accept facts only when MAL work identity has an EXACT existing ID link.

    No title-based join. No implicit French translation. Relations aren't merges.
    """
    mid=checked_int(mal_id)
    if provider not in SOURCES or not mid or not source_id or not url.startswith("https://"):
        raise ValueError("Invalid provider or authoritative MAL reference")
    with conn.cursor() as cur:
        cur.execute("""SELECT id FROM catalogue_work
                       WHERE origin_source='MAL' AND origin_id=%s""",(str(mid),))
        row=cur.fetchone()
        if not row:
            return {"status":"MAL_WORK_MISSING","stored":0}
        work_id=int(row["id"])
        cur.execute(ID_CLAIM_SQL,{
            "work_id":work_id,"provider":provider,
            "external_id":str(source_id),"source_name":provider,
            "evidence_url":url,
        })
        cur.execute(IDENTITY_COLLISIONS_SQL)
        added=1
        for record in (titles or [])[:40]:
            language=LANGUAGES.get(record.get("language") or record.get("language_code"))
            title=str(record.get("title") or record.get("alias") or "").strip()
            if not language or not 2<=len(title)<=200:
                continue
            cur.execute(TITLE_CLAIM_SQL,{
                "work_id":work_id,"source_name":provider,
                "source_id":str(source_id),"language_code":language,
                "title":title,"title_key":title_key(title),
                "evidence_url":url,
            })
            cur.execute("""
              UPDATE catalogue_title_claim claim
              SET evidence_status='COLLISION_REVIEW'
              WHERE claim.work_id=%s AND claim.source_name=%s
                AND claim.source_id=%s
                AND EXISTS (
                  SELECT 1 FROM catalogue_work other
                  WHERE other.id<>claim.work_id AND
                    lower(btrim(other.canonical_title))=claim.title_key
                )
            """,(work_id,provider,str(source_id)))
            added+=1
        for relation in (relations or [])[:40]:
            target=checked_int(relation.get("mal_id")) or checked_int(relation.get("anilist_id"))
            target_type=str(relation.get("media_type") or "MANGA").lower()
            rtype=str(relation.get("relation_type") or "")
            if not target or target_type not in ("manga","anime") or not re.fullmatch(r"[A-Z_]{2,32}",rtype):
                continue
            cur.execute(RELATION_CLAIM_SQL,{
                "work_id":work_id,"source_name":provider,
                "source_work_id":str(source_id),"relation_type":rtype,
                "target_provider":"MAL" if checked_int(relation.get("mal_id")) else "ANILIST",
                "target_external_id":str(target),
                "target_media_type":target_type,"evidence_url":url,
            })
            added+=1
    return {"status":"STAGED_SOURCE_CLAIMS","stored":added,
            "work_id":work_id,"ownership_modified":False,
            "identities_merged":False}
),
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  title_fr TEXT NOT NULL,
  author_fr TEXT,
  publisher_fr TEXT,
  language_recorded TEXT,
  evidence_status TEXT NOT NULL DEFAULT 'BIBLIOGRAPHIC_CANDIDATE'
    CHECK (evidence_status IN ('BIBLIOGRAPHIC_CANDIDATE',
                              'MULTI_WORK_ISBN_REVIEW','REJECTED','VERIFIED')),
  PRIMARY KEY(work_id,isbn13,source_name)
);
CREATE INDEX IF NOT EXISTS catalogue_book_claim_isbn_idx
 ON catalogue_book_claim(isbn13);
CREATE TABLE IF NOT EXISTS catalogue_work_relation (
  work_id BIGINT NOT NULL REFERENCES catalogue_work(id) ON DELETE CASCADE,
  source_name TEXT NOT NULL,
  source_work_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  target_provider TEXT NOT NULL,
  target_external_id TEXT NOT NULL,
  target_media_type TEXT NOT NULL DEFAULT 'manga',
  evidence_url TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(work_id,source_name,relation_type,target_provider,target_external_id)
);
"""

# Rebuild from Jikan/MAL identity + current alias data, WITHOUT deleting raw
# evidence, existing manga rows or previously quarantined claims.
BASE_BACKFILL = """
INSERT INTO catalogue_work(legacy_manga_id,origin_source,origin_id,canonical_title)
SELECT m.id,'MAL',m.source_mal_id::text,m.title FROM manga m
ON CONFLICT(origin_source,origin_id) DO UPDATE
 SET canonical_title=EXCLUDED.canonical_title,updated_at=now()
 WHERE catalogue_work.canonical_title IS DISTINCT FROM EXCLUDED.canonical_title;

INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
SELECT w.id,'MAL','manga',m.source_mal_id::text,'JIKAN_MAL',
       'https://myanimelist.net/manga/'||m.source_mal_id,'VERIFIED'
FROM catalogue_work w JOIN manga m ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;

INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
SELECT w.id,'JIKAN_MAL',m.source_mal_id::text,'und',
       left(m.title,500),lower(btrim(left(m.title,500))),
       'CANONICAL','CANONICAL','https://myanimelist.net/manga/'||m.source_mal_id
FROM catalogue_work w JOIN manga m ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;

INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
SELECT w.id,a.source_name,a.source_id,a.language_code,a.alias,a.alias_key,
  CASE WHEN a.source_name='TENRAI_MAL' THEN 'UNVERIFIED_SYNONYM'
       WHEN a.source_name='TENRAI_MAL_TYPED' THEN 'TYPED_TITLE'
       ELSE 'EXTERNAL_TITLE' END,
  CASE
    -- Conflict with ANY other canonical work title: never auto-accept.
    WHEN EXISTS (
      SELECT 1 FROM manga other WHERE other.id <> w.legacy_manga_id
       AND lower(btrim(other.title))=lower(btrim(a.alias))
    ) THEN 'COLLISION_REVIEW'
    -- Jikan's untyped synonyms can be chapter titles / anthology entries.
    WHEN a.source_name='TENRAI_MAL' THEN 'DISCOVERY_ONLY'
    -- Typed and cross-ID-source names are attributed CLAIMS, not verified work.
    ELSE 'SOURCE_LINKED'
  END,
  a.source_url
FROM manga_title_alias a
JOIN catalogue_work w ON w.legacy_manga_id=a.manga_id
WHERE length(btrim(a.alias)) BETWEEN 1 AND 500
ON CONFLICT(work_id,source_name,language_code,claim_kind,title_key)
DO UPDATE SET
  title=EXCLUDED.title,
  source_id=EXCLUDED.source_id,
  evidence_url=EXCLUDED.evidence_url,
  evidence_status=CASE
    WHEN catalogue_title_claim.evidence_status IN ('REJECTED','VERIFIED')
      THEN catalogue_title_claim.evidence_status
    ELSE EXCLUDED.evidence_status END;

INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
SELECT w.id,'WIKIDATA','manga',f.wikidata_id,'WIKIDATA_P4087',
       'https://www.wikidata.org/wiki/'||f.wikidata_id,'SOURCE_CLAIM'
FROM manga_wikidata_fact f
JOIN manga m ON m.id=f.manga_id AND m.source_mal_id=f.source_mal_id
JOIN catalogue_work w ON w.legacy_manga_id=m.id
ON CONFLICT DO NOTHING;
"""

# Exact identifiers may identify the SAME work across sources, but imported
# community IDs are source claims pending cross-check, not automatic merges.
ID_CLAIM_SQL = """
INSERT INTO catalogue_work_identifier
(work_id,provider,media_type,external_id,source_name,evidence_url,identity_status)
VALUES (%(work_id)s,%(provider)s,'manga',%(external_id)s,
        %(source_name)s,%(evidence_url)s,'SOURCE_CLAIM')
ON CONFLICT DO NOTHING
"""
IDENTITY_COLLISIONS_SQL = """
UPDATE catalogue_work_identifier ident SET identity_status='COLLISION_REVIEW'
WHERE ident.identity_status <> 'REJECTED'
  AND EXISTS (
    SELECT 1 FROM catalogue_work_identifier other
    WHERE other.provider=ident.provider AND other.media_type=ident.media_type
      AND other.external_id=ident.external_id AND other.work_id<>ident.work_id
  )
"""
TITLE_CLAIM_SQL = """
INSERT INTO catalogue_title_claim
(work_id,source_name,source_id,language_code,title,title_key,
 claim_kind,evidence_status,evidence_url)
VALUES (%(work_id)s,%(source_name)s,%(source_id)s,%(language_code)s,
        %(title)s,%(title_key)s,'EXTERNAL_TITLE','SOURCE_LINKED',
        %(evidence_url)s)
ON CONFLICT DO NOTHING
"""
RELATION_CLAIM_SQL = """
INSERT INTO catalogue_work_relation
(work_id,source_name,source_work_id,relation_type,target_provider,
 target_external_id,target_media_type,evidence_url)
VALUES (%(work_id)s,%(source_name)s,%(source_work_id)s,%(relation_type)s,
        %(target_provider)s,%(target_external_id)s,%(target_media_type)s,
        %(evidence_url)s)
ON CONFLICT DO NOTHING
"""

SOURCES = frozenset({"ANILIST","KITSU","MANGADEX","WIKIDATA"})
LANGUAGES = {"romaji":"ja-ro","english":"en","native":"ja",
             "en":"en","fr":"fr","ja":"ja","ja-ro":"ja-ro"}


def title_key(title: str) -> str:
    t=unicodedata.normalize("NFKC",str(title or "")).casefold()
    return " ".join(t.split())[:500]


def checked_int(value: Any) -> int | None:
    if type(value) not in (int,str):
        return None
    text=str(value)
    return int(text) if re.fullmatch(r"[1-9][0-9]{0,9}",text) else None


def ensure_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA)


def rebuild_legacy_sources(conn: Any) -> None:
    """Idempotent, source-preserving rebuild. Caller chooses commit/rollback."""
    with conn.cursor() as cur:
        cur.execute(BASE_BACKFILL)
        cur.execute(IDENTITY_COLLISIONS_SQL)


def register_non_mal_work(conn: Any, title: str, *,
                          source: str, external_id: str) -> int:
    """Allow French-native works (e.g. Radiant) without a fake MAL ID."""
    if source not in ("BNF","WIKIDATA","PUBLISHER"):
        raise ValueError("A documented primary source is required.")
    if not title.strip() or not external_id or len(external_id)>150:
        raise ValueError("A verifiable bibliographic source reference is required.")
    with conn.cursor() as cur:
        cur.execute("""
           INSERT INTO catalogue_work
             (legacy_manga_id,origin_source,origin_id,canonical_title)
           VALUES(NULL,%s,%s,%s)
           ON CONFLICT(origin_source,origin_id) DO UPDATE
           SET canonical_title=EXCLUDED.canonical_title
           RETURNING id
        """,(source,external_id,title.strip()))
        return int(cur.fetchone()["id"])


def stage_external_facts(conn: Any, mal_id: int, *,
                         provider: str, source_id: str,
                         url: str, titles: list[dict[str,str]] | None = None,
                         relations: list[dict[str,Any]] | None = None) -> dict:
    """Accept facts only when MAL work identity has an EXACT existing ID link.

    No title-based join. No implicit French translation. Relations aren't merges.
    """
    mid=checked_int(mal_id)
    if provider not in SOURCES or not mid or not source_id or not url.startswith("https://"):
        raise ValueError("Invalid provider or authoritative MAL reference")
    with conn.cursor() as cur:
        cur.execute("""SELECT id FROM catalogue_work
                       WHERE origin_source='MAL' AND origin_id=%s""",(str(mid),))
        row=cur.fetchone()
        if not row:
            return {"status":"MAL_WORK_MISSING","stored":0}
        work_id=int(row["id"])
        cur.execute(ID_CLAIM_SQL,{
            "work_id":work_id,"provider":provider,
            "external_id":str(source_id),"source_name":provider,
            "evidence_url":url,
        })
        cur.execute(IDENTITY_COLLISIONS_SQL)
        added=1
        for record in (titles or [])[:40]:
            language=LANGUAGES.get(record.get("language") or record.get("language_code"))
            title=str(record.get("title") or record.get("alias") or "").strip()
            if not language or not 2<=len(title)<=200:
                continue
            cur.execute(TITLE_CLAIM_SQL,{
                "work_id":work_id,"source_name":provider,
                "source_id":str(source_id),"language_code":language,
                "title":title,"title_key":title_key(title),
                "evidence_url":url,
            })
            cur.execute("""
              UPDATE catalogue_title_claim claim
              SET evidence_status='COLLISION_REVIEW'
              WHERE claim.work_id=%s AND claim.source_name=%s
                AND claim.source_id=%s
                AND EXISTS (
                  SELECT 1 FROM catalogue_work other
                  WHERE other.id<>claim.work_id AND
                    lower(btrim(other.canonical_title))=claim.title_key
                )
            """,(work_id,provider,str(source_id)))
            added+=1
        for relation in (relations or [])[:40]:
            target=checked_int(relation.get("mal_id")) or checked_int(relation.get("anilist_id"))
            target_type=str(relation.get("media_type") or "MANGA").lower()
            rtype=str(relation.get("relation_type") or "")
            if not target or target_type not in ("manga","anime") or not re.fullmatch(r"[A-Z_]{2,32}",rtype):
                continue
            cur.execute(RELATION_CLAIM_SQL,{
                "work_id":work_id,"source_name":provider,
                "source_work_id":str(source_id),"relation_type":rtype,
                "target_provider":"MAL" if checked_int(relation.get("mal_id")) else "ANILIST",
                "target_external_id":str(target),
                "target_media_type":target_type,"evidence_url":url,
            })
            added+=1
    return {"status":"STAGED_SOURCE_CLAIMS","stored":added,
            "work_id":work_id,"ownership_modified":False,
            "identities_merged":False}
