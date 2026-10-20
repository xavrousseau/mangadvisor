"""Import official BnF UNIMARC UTF-8 ISO 2709 books into isolated evidence staging.

Does not match works/editions, create ISBN ownership, or touch private library
tables. Files must be downloaded manually from BnF and placed under data/raw.
The importer operates wholly inside the disposable Docker engine container.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import unicodedata
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator

from pipelines.engine.src.load.postgres_loader import get_postgres_connection

ROOT = Path(__file__).resolve().parents[3]
IMPORTS = ROOT / "data" / "raw" / "bnf" / "imports"
SOURCE_URL = "https://api.bnf.fr/index.php/fr/produits_bibliographiques_mensuels"
SUPPORTED = (".not", ".mrc", ".iso", ".marc", ".gz", ".zip")
RECORD_LIMIT = 99_999
BATCH_SIZE = 200

# Staging is strictly separated from canonical manga, confirmed editions
# and all user ownership/reading tables.
DDL = """
CREATE TABLE IF NOT EXISTS bnf_bulk_batch (
 source_sha256 CHAR(64) PRIMARY KEY,
 file_name TEXT NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('COMPLETED')),
 scanned INTEGER NOT NULL,
 candidates INTEGER NOT NULL,
 isbn_candidates INTEGER NOT NULL,
 imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bnf_bulk_notice (
 notice_id TEXT PRIMARY KEY,
 title TEXT NOT NULL,
 author TEXT,
 publisher TEXT,
 publication_year TEXT,
 collection_title TEXT,
 volume_label TEXT,
 subjects TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 isbn13 TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 match_evidence TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 cataloguing_agency TEXT,
 notice_date TEXT,
 source_name TEXT NOT NULL DEFAULT 'BnF',
 source_url TEXT NOT NULL,
 retrieved_at TIMESTAMPTZ NOT NULL,
 source_sha256 CHAR(64) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bnf_bulk_notice_isbn
 ON bnf_bulk_notice USING GIN (isbn13);
"""

UPSERT = """
INSERT INTO bnf_bulk_notice (
 notice_id,title,author,publisher,publication_year,collection_title,
 volume_label,subjects,isbn13,match_evidence,cataloguing_agency,
 notice_date,source_url,retrieved_at,source_sha256
) VALUES (
 %(notice_id)s,%(title)s,%(author)s,%(publisher)s,%(publication_year)s,
 %(collection_title)s,%(volume_label)s,%(subjects)s,%(isbn13)s,
 %(match_evidence)s,%(cataloguing_agency)s,%(notice_date)s,
 %(source_url)s,%(retrieved_at)s,%(source_sha256)s
)
ON CONFLICT (notice_id) DO UPDATE SET
 title=EXCLUDED.title,author=EXCLUDED.author,publisher=EXCLUDED.publisher,
 publication_year=EXCLUDED.publication_year,
 collection_title=EXCLUDED.collection_title,volume_label=EXCLUDED.volume_label,
 subjects=EXCLUDED.subjects,isbn13=EXCLUDED.isbn13,
 match_evidence=EXCLUDED.match_evidence,cataloguing_agency=EXCLUDED.cataloguing_agency,
 notice_date=EXCLUDED.notice_date,source_url=EXCLUDED.source_url,
 retrieved_at=EXCLUDED.retrieved_at,source_sha256=EXCLUDED.source_sha256
"""

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_iso2709(reader: BinaryIO) -> Iterator[bytes]:
    """Read length-prefixed ISO 2709 records, rejecting truncated/corrupt input."""
    while True:
        leader = reader.read(24)
        if not leader:
            return
        if len(leader) != 24 or not leader[:5].isdigit():
            raise ValueError("ISO 2709: en-tête de notice invalide ou tronqué")
        size = int(leader[:5])
        if size < 26 or size > RECORD_LIMIT:
            raise ValueError("ISO 2709: longueur de notice incorrecte")
        body = reader.read(size - 24)
        if len(body) != size - 24 or not body.endswith(b"\x1d"):
            raise ValueError("ISO 2709: notice incomplète ou terminateur absent")
        yield leader + body


@contextmanager
def open_bnf_stream(path: Path):
    """Yield one or several UTF-8 ISO 2709 streams without writing archive contents."""
    suffix = path.name.lower()
    if suffix.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            members = [i for i in archive.infolist()
                       if not i.is_dir() and i.filename.lower().endswith((".not", ".mrc", ".iso", ".marc"))]
            if not members or len(members) > 100:
                raise ValueError("Archive ZIP sans notices UNIMARC ou trop de fichiers")
            # Reject zip bombs and encrypted members before streaming.
            if any(m.flag_bits & 1 or m.file_size > 3_000_000_000 or
                   (m.file_size > 50_000_000 and m.file_size > 500 * max(1, m.compress_size))
                   for m in members):
                raise ValueError("Archive ZIP chiffrée ou anormalement volumineuse")
            yield [(m.filename, archive.open(m)) for m in members]
    elif suffix.endswith(".gz"):
        with gzip.open(path, "rb") as f:
            yield [(path.name, f)]
    else:
        with path.open("rb") as f:
            yield [(path.name, f)]


def iter_file_records(path: Path) -> Iterator[bytes]:
    with open_bnf_stream(path) as streams:
        try:
            for _, stream in streams:
                yield from iter_iso2709(stream)
        finally:
            for _, stream in streams:
                stream.close()


def fields_from_record(record: bytes) -> dict[str, list[dict[str, list[str]]]]:
    """Decode UNIMARC directory/field boundaries (2 indicator bytes per datafield)."""
    leader = record[:24]
    if not leader[12:17].isdigit():
        raise ValueError("ISO 2709: base de données invalide")
    base = int(leader[12:17])
    if base <= 25 or base >= len(record) or record[base - 1:base] != b"\x1e":
        raise ValueError("ISO 2709: répertoire invalide")
    directory = record[24:base - 1]
    if len(directory) % 12:
        raise ValueError("ISO 2709: entrées de répertoire incorrectes")
    output: dict[str, list[dict[str, list[str]]]] = {}
    for offset in range(0, len(directory), 12):
        entry = directory[offset:offset + 12]
        if not (entry[:3].isdigit() and entry[3:12].isdigit()):
            raise ValueError("ISO 2709: entrée de répertoire invalide")
        tag = entry[:3].decode("ascii")
        length, pos = int(entry[3:7]), int(entry[7:12])
        data = record[base + pos:base + pos + length]
        if len(data) != length or not data.endswith(b"\x1e"):
            raise ValueError("ISO 2709: champ hors de la notice")
        item: dict[str, list[str]] = {}
        raw = data[:-1]
        if int(tag) < 10:
            item["value"] = [raw.decode("utf-8").strip()]
        else:
            # UNIMARC uses two indicator bytes and \x1f<code> subfields.
            for part in raw[2:].split(b"\x1f")[1:]:
                if not part:
                    continue
                code = part[:1].decode("ascii", errors="replace")
                item.setdefault(code, []).append(part[1:].decode("utf-8").strip())
        output.setdefault(tag, []).append(item)
    return output


def values(fields: dict, tag: str, code: str) -> list[str]:
    return [v for field in fields.get(tag, []) for v in field.get(code, []) if v]


def first(fields: dict, tag: str, code: str) -> str | None:
    return next(iter(values(fields, tag, code)), None)


def isbn13(raw: str) -> str | None:
    """Validate ISBN-13 or ISBN-10, converting a valid ISBN-10 to 978 ISBN-13."""
    # The $a of UNIMARC 010 should carry ISBN, sometimes followed by "(br.)".
    candidate = re.split(r"[(;]", raw, maxsplit=1)[0]
    code = re.sub(r"[\s-]", "", candidate).upper()
    if len(code) == 10 and re.fullmatch(r"\d{9}[\dX]", code):
        total = sum((10 - i) * int(c) for i, c in enumerate(code[:9]))
        total += 10 if code[-1] == "X" else int(code[-1])
        if total % 11:
            return None
        code = "978" + code[:9]
        check = (10 - sum(int(c) * (1 if i % 2 == 0 else 3)
                          for i, c in enumerate(code)) % 10) % 10
        return code + str(check)
    if len(code) != 13 or not code.isdigit() or not code.startswith(("978", "979")):
        return None
    checksum = sum(int(c) * (1 if i % 2 == 0 else 3)
                   for i, c in enumerate(code[:12]))
    return code if (checksum + int(code[-1])) % 10 == 0 else None


def normalize_text(raw: str) -> str:
    text = unicodedata.normalize("NFKD", raw.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def parse_candidate(record: bytes, sha: str, now: datetime) -> dict | None:
    fields = fields_from_record(record)
    notice_id = first(fields, "001", "value")
    title = first(fields, "200", "a")
    if not notice_id or not title or len(notice_id) > 120:
        return None

    subjects = [*values(fields, "606", "a"), *values(fields, "606", "x"),
                *values(fields, "608", "a")]
    collection = first(fields, "225", "a")
    publisher = first(fields, "214", "c") or first(fields, "210", "c")
    # Publisher alone is never evidence: major publishers also publish non-manga.
    signals = ["sujet:" + item for item in subjects
               if re.search(r"\bmangas?\b|bandes? dessinees? japonaises?", normalize_text(item))]
    if collection and re.search(r"\bmangas?\b", normalize_text(collection)):
        signals.append("collection:" + collection)
    if not signals:
        return None

    codes = sorted({parsed for original in values(fields, "010", "a")
                    if (parsed := isbn13(original))})
    return {
        "notice_id": notice_id, "title": title,
        "author": first(fields, "200", "f") or first(fields, "700", "a"),
        "publisher": publisher,
        "publication_year": first(fields, "214", "d") or first(fields, "210", "d"),
        "collection_title": collection, "volume_label": first(fields, "225", "v"),
        "subjects": subjects, "isbn13": codes, "match_evidence": signals,
        "cataloguing_agency": first(fields, "801", "b"),
        "notice_date": first(fields, "801", "c"),
        "source_url": SOURCE_URL, "retrieved_at": now, "source_sha256": sha,
    }


def ingest_one(path: Path, *, preview: bool = False, database=None) -> dict:
    if not path.is_file() or path.is_symlink() or not path.name.lower().endswith(SUPPORTED):
        raise ValueError("Fichier BnF local non pris en charge")
    sha = sha256_file(path)
    now = datetime.now(timezone.utc)
    if not preview:
        if database is None:
            raise ValueError("Connexion PostgreSQL requise pour l'import")
        with database.cursor() as cur:
            cur.execute(DDL)
            cur.execute("SELECT status FROM bnf_bulk_batch WHERE source_sha256=%s", (sha,))
            if cur.fetchone():
                database.commit()
                return {"file": path.name, "status": "ALREADY_IMPORTED", "sha256": sha}
        database.commit()

    scanned = candidates = with_isbn = 0
    pending = []
    # One file == one atomic transaction: a corrupt file never partly replaces
    # the staged catalogue. No rows of the private library are ever modified.
    try:
        with database.transaction() if not preview else _no_transaction():
            for record in iter_file_records(path):
                scanned += 1
                if preview and scanned > 1000:
                    break
                row = parse_candidate(record, sha, now)
                if row is None:
                    continue
                candidates += 1
                with_isbn += bool(row["isbn13"])
                if preview:
                    if candidates <= 5:
                        print("   Exemple :", row["title"], "|", ", ".join(row["isbn13"]) or "ISBN absent")
                else:
                    pending.append(row)
                    if len(pending) >= BATCH_SIZE:
                        with database.cursor() as cur:
                            cur.executemany(UPSERT, pending)
                        pending.clear()
            if not preview:
                with database.cursor() as cur:
                    if pending:
                        cur.executemany(UPSERT, pending)
                    cur.execute(
                        """INSERT INTO bnf_bulk_batch
                           (source_sha256,file_name,status,scanned,candidates,isbn_candidates)
                           VALUES (%s,%s,'COMPLETED',%s,%s,%s)""",
                        (sha, path.name, scanned, candidates, with_isbn),
                    )
    except Exception:
        if not preview:
            database.rollback()
        raise
    if not preview:
        database.commit()
    return {"file": path.name, "status": "PREVIEW_1000" if preview else "IMPORTED",
            "sha256": sha, "scanned": scanned, "candidates": candidates,
            "with_isbn": with_isbn}


@contextmanager
def _no_transaction():
    yield


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import BnF UNIMARC UTF-8 ISO 2709 (staging seulement)")
    parser.add_argument("--input-dir", type=Path, default=IMPORTS)
    parser.add_argument("--preview", action="store_true", help="Aperçu jusqu'à 1000 notices/fichier sans écrire")
    parser.add_argument("--max-files", type=int, default=20)
    args = parser.parse_args(argv)
    if not 1 <= args.max_files <= 50:
        parser.error("max-files : entre 1 et 50")
    if not args.input_dir.is_dir():
        print("Dossier BnF absent :", args.input_dir)
        return 2
    files = sorted(p for p in args.input_dir.iterdir()
                   if p.is_file() and p.name.lower().endswith(SUPPORTED))
    if not files:
        print("Aucun fichier BnF ISO 2709 à importer dans", args.input_dir)
        return 2
    if len(files) > args.max_files:
        print("Trop de fichiers :", len(files), "limite", args.max_files, "- traiter en plusieurs lots")
        return 2
    db = None if args.preview else get_postgres_connection()
    try:
        for file in files:
            result = ingest_one(file, preview=args.preview, database=db)
            print(json.dumps(result, ensure_ascii=False))
    finally:
        if db:
            db.close()
    print("Aucune édition française, aucune collection utilisateur modifiée.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        print("Import BnF interrompu sans import partiel :", exc, file=sys.stderr)
        sys.exit(1)
