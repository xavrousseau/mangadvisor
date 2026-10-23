-- Mangadvisor V2 : modèle de la base BIBLIOGRAPHIQUE.
-- Doit être exécuté exclusivement sur un nouveau PostgreSQL isolé.
-- Jamais sur la base stable du projet historique.
BEGIN;

CREATE TABLE source_record (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  provider TEXT NOT NULL,
  source_key TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sha256 CHAR(64) NOT NULL,
  UNIQUE(provider, resource_type, source_key, sha256)
);

CREATE TABLE work (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  work_type TEXT NOT NULL CHECK(work_type IN
    ('MANGA','ONE_SHOT','ANTHOLOGY','LIGHT_NOVEL','MANHWA','MANHUA','OTHER')),
  preferred_title TEXT NOT NULL CHECK(length(btrim(preferred_title))>0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE external_identifier (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  work_id BIGINT NOT NULL REFERENCES work(id),
  provider TEXT NOT NULL,
  media_type TEXT NOT NULL,
  external_id TEXT NOT NULL,
  source_record_id BIGINT NOT NULL REFERENCES source_record(id),
  decision TEXT NOT NULL CHECK(decision IN ('CLAIM','CONFIRMED','CONFLICT','REJECTED')),
  UNIQUE(work_id,provider,media_type,external_id,source_record_id)
);
-- One externally scoped identifier cannot CONFIRM two different works.
CREATE UNIQUE INDEX confirmed_external_id_unique
 ON external_identifier(provider,media_type,external_id)
 WHERE decision='CONFIRMED';

CREATE TABLE title_claim (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  work_id BIGINT NOT NULL REFERENCES work(id),
  title TEXT NOT NULL CHECK(length(btrim(title))>0),
  lang TEXT NOT NULL DEFAULT 'und',
  kind TEXT NOT NULL CHECK(kind IN ('CANONICAL','ALTERNATE','SYNONYM','CHAPTER')),
  source_record_id BIGINT NOT NULL REFERENCES source_record(id),
  decision TEXT NOT NULL CHECK(decision IN
    ('CONFIRMED','CANDIDATE','DISCOVERY_ONLY','CONFLICT','REJECTED')),
  UNIQUE(work_id,title,lang,kind,source_record_id)
);
CREATE INDEX title_claim_search_idx ON title_claim(lower(title));

CREATE TABLE work_relation (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_work_id BIGINT NOT NULL REFERENCES work(id),
  target_work_id BIGINT NOT NULL REFERENCES work(id),
  relation_type TEXT NOT NULL CHECK(relation_type IN
    ('SEQUEL','PREQUEL','SPIN_OFF','SIDE_STORY','ADAPTATION','OTHER')),
  source_record_id BIGINT NOT NULL REFERENCES source_record(id),
  decision TEXT NOT NULL CHECK(decision IN('CANDIDATE','CONFIRMED','REJECTED')),
  CHECK(source_work_id<>target_work_id)
);

CREATE TABLE bibliographic_record (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  provider TEXT NOT NULL,
  provider_record_id TEXT NOT NULL,
  isbn13 CHAR(13),
  title TEXT NOT NULL,
  publisher TEXT,
  publication_date DATE,
  raw_source_record_id BIGINT NOT NULL REFERENCES source_record(id),
  UNIQUE(provider,provider_record_id),
  CHECK(isbn13 IS NULL OR isbn13 ~ '^[0-9]{13}$')
);

CREATE TABLE edition (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  work_id BIGINT NOT NULL REFERENCES work(id),
  market TEXT NOT NULL DEFAULT 'FR',
  publisher TEXT NOT NULL,
  collection TEXT,
  edition_name TEXT NOT NULL,
  format_name TEXT,
  decision TEXT NOT NULL CHECK(decision IN('CANDIDATE','CONFIRMED','REJECTED'))
);
CREATE TABLE publication (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edition_id BIGINT NOT NULL REFERENCES edition(id),
  volume_label TEXT,
  isbn13 CHAR(13),
  bibliographic_record_id BIGINT NOT NULL REFERENCES bibliographic_record(id),
  decision TEXT NOT NULL CHECK(decision IN('CANDIDATE','CONFIRMED','REJECTED')),
  CHECK(isbn13 IS NULL OR isbn13 ~ '^[0-9]{13}$')
);
CREATE UNIQUE INDEX unique_confirmed_isbn13
 ON publication(isbn13) WHERE isbn13 IS NOT NULL AND decision='CONFIRMED';

CREATE TABLE resolution_review (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  object_type TEXT NOT NULL,
  source_record_id BIGINT REFERENCES source_record(id),
  candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN('OPEN','RESOLVED','REJECTED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Private inventory depends on PUBLIC edition/publication but never creates
-- work identities or official ISBN from its user-supplied title.
CREATE TABLE owned_item (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_row_key TEXT UNIQUE,
  declared_title TEXT NOT NULL,
  declared_edition TEXT,
  declared_volume TEXT,
  quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity>=0),
  confirmed_publication_id BIGINT REFERENCES publication(id),
  resolution_status TEXT NOT NULL CHECK(resolution_status IN
    ('PENDING','CONFIRMED','REJECTED'))
);
CREATE TABLE import_run (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  stage TEXT NOT NULL,
  source_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN('STARTED','DONE','FAILED')),
  seen INTEGER NOT NULL DEFAULT 0,
  accepted INTEGER NOT NULL DEFAULT 0,
  rejected INTEGER NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

COMMIT;
