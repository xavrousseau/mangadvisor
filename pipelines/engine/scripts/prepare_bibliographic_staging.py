"""Bibliographic staging V1: import a vetted local benchmark V2 JSON into isolated SQL.

No canonical manga, edition, inventory, library or recommendation table is
changed. No remote API calls. Every result stays REVIEW_REQUIRED; an ISBN
match with BnF means corroborating bibliographic evidence, NOT ownership.

CLI: --preview (no DB); --import (isolated staging only); --status (read DB).
Input is a single benchmark JSON in data/logs/catalog_sources; default latest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.engine.src.load.postgres_loader import get_postgres_connection
from pipelines.engine.scripts.bnf_bulk_import import isbn13
from pipelines.engine.scripts.catalogue_french_matching import edition_family
from apps.api.app.bnf_edition_audit import volume_from_title

ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = ROOT / "data" / "logs" / "catalog_sources"
OUTPUT_DIR = ROOT / "data" / "logs" / "bibliographic_staging"
MAX_BYTES = 18_000_000
MAX_ENTRIES = 50
PROVIDERS = ("scrinis", "mangaupdates")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
FILENAME_RE = re.compile(r"^comparatif_sources_v2_[\d_]+\.json$")

# Only new names beginning bib_stage_ may be inserted, updated or deleted.
# Full report (including user inventory) is intentionally NOT persisted.
DDL = """
CREATE TABLE IF NOT EXISTS bib_stage_batch (
 source_sha256 CHAR(64) PRIMARY KEY,
 report_file TEXT NOT NULL,
 generated_at TEXT,
 entry_count INTEGER NOT NULL CHECK (entry_count BETWEEN 1 AND 50),
 status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
   CHECK (status = 'REVIEW_REQUIRED'),
 imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS bib_stage_candidate (
 id BIGSERIAL PRIMARY KEY,
 source_sha256 CHAR(64) NOT NULL REFERENCES bib_stage_batch(source_sha256),
 entry_position INTEGER NOT NULL CHECK (entry_position BETWEEN 1 AND 50),
 input_title TEXT NOT NULL,
 origin TEXT NOT NULL CHECK (origin IN ('pending','owned','catalog')),
 market_target TEXT NOT NULL CHECK (market_target IN ('FR_PRINT','INTERNATIONAL')),
 provider TEXT NOT NULL CHECK (provider IN ('scrinis','mangaupdates')),
 external_id TEXT NOT NULL,
 candidate_title TEXT NOT NULL,
 work_type TEXT,
 evidence TEXT NOT NULL CHECK (evidence IN ('EXACT_TITLE','SAME_MAL_ID','SUGGESTION_ONLY')),
 search_status TEXT NOT NULL,
 source_detail_status TEXT NOT NULL,
 work_score SMALLINT CHECK (work_score BETWEEN 0 AND 100),
 edition_score SMALLINT CHECK (edition_score BETWEEN 0 AND 100),
 authors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 publishers TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 genres TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 themes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 aliases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 edition_declarations TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
 reference_count_reported INTEGER,
 reference_list_truncated BOOLEAN NOT NULL DEFAULT FALSE,
 decision TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED'
   CHECK (decision = 'REVIEW_REQUIRED'),
 UNIQUE (source_sha256,entry_position,provider,external_id)
);
CREATE TABLE IF NOT EXISTS bib_stage_edition (
 id BIGSERIAL PRIMARY KEY,
 candidate_id BIGINT NOT NULL REFERENCES bib_stage_candidate(id),
 lang TEXT NOT NULL,
 medium TEXT NOT NULL,
 edition_label TEXT NOT NULL,
 volume_count INTEGER CHECK (volume_count IS NULL OR volume_count >= 0),
 UNIQUE(candidate_id,lang,medium,edition_label)
);
CREATE TABLE IF NOT EXISTS bib_stage_volume (
 id BIGSERIAL PRIMARY KEY,
 candidate_id BIGINT NOT NULL REFERENCES bib_stage_candidate(id),
 isbn13 CHAR(13) NOT NULL CHECK (isbn13 ~ '^[0-9]{13}$'),
 lang TEXT NOT NULL,
 medium TEXT NOT NULL,
 edition_label TEXT NOT NULL,
 volume_label TEXT NOT NULL,
 released_on TEXT,
 UNIQUE(candidate_id,isbn13,lang,medium,edition_label,volume_label)
);
CREATE INDEX IF NOT EXISTS idx_bib_stage_candidate_batch
 ON bib_stage_candidate(source_sha256,entry_position);
CREATE INDEX IF NOT EXISTS idx_bib_stage_volume_isbn
 ON bib_stage_volume(isbn13);
"""

CANDIDATE_INSERT = """
INSERT INTO bib_stage_candidate (
 source_sha256,entry_position,input_title,origin,market_target,provider,
 external_id,candidate_title,work_type,evidence,search_status,
 source_detail_status,work_score,edition_score,authors,publishers,
 genres,themes,aliases,edition_declarations,reference_count_reported,
 reference_list_truncated
) VALUES (
 %(sha)s,%(position)s,%(input_title)s,%(origin)s,%(market_target)s,%(provider)s,
 %(external_id)s,%(title)s,%(work_type)s,%(evidence)s,%(search_status)s,
 %(detail_status)s,%(work_score)s,%(edition_score)s,%(authors)s,%(publishers)s,
 %(genres)s,%(themes)s,%(aliases)s,%(edition_declarations)s,%(reference_count)s,
 %(reference_truncated)s
) RETURNING id
"""
EDITION_INSERT = """
INSERT INTO bib_stage_edition (candidate_id,lang,medium,edition_label,volume_count)
VALUES (%s,%s,%s,%s,%s)
ON CONFLICT (candidate_id,lang,medium,edition_label) DO NOTHING
"""
VOLUME_INSERT = """
INSERT INTO bib_stage_volume (
 candidate_id,isbn13,lang,medium,edition_label,volume_label,released_on
) VALUES (%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (candidate_id,isbn13,lang,medium,edition_label,volume_label)
DO NOTHING
"""


def clean(value: Any, maxlen: int = 200) -> str:
    return str(value).strip()[:maxlen] if isinstance(value, (str, int, float)) else ""


def strings(items: Any, *, maximum: int = 20, length: int = 150) -> list[str]:
    if not isinstance(items, list):
        return []
    return list(dict.fromkeys(x for raw in items[:100]
                              if (x := clean(raw, length))))[:maximum]


def select_report(name: str | None, base: Path = INPUT_DIR) -> Path:
    if name is not None and not FILENAME_RE.fullmatch(name):
        raise ValueError("Nom de rapport invalide : choisir un JSON V2 dans data/logs/catalog_sources")
    if not base.is_dir():
        raise ValueError("Aucun rapport V2 sur ce PC. Exécuter A -> 17.")
    if name:
        candidate = base / name
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError("Rapport local introuvable ou lien interdit")
        return candidate
    candidates = [f for f in base.iterdir() if f.is_file() and not f.is_symlink()
                  and FILENAME_RE.fullmatch(f.name)]
    if not candidates:
        raise ValueError("Aucun rapport V2 trouvé : exécuter A -> 17 avant le staging")
    # Generated timestamps in filenames are UTC and sortable.
    return max(candidates, key=lambda f: f.name)


def read_report(path: Path) -> tuple[str, dict]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Rapport absent, lien interdit ou dépasse 18 Mo")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw)
    if (not isinstance(doc, dict) or doc.get("format_version") != 2 or
            not isinstance(doc.get("entries"), list) or not 1 <= len(doc["entries"]) <= MAX_ENTRIES or
            doc.get("sample_count") != len(doc["entries"])):
        raise ValueError("Rapport V2 invalide ou taille d'échantillon incohérente")
    if not isinstance(doc.get("providers"), dict):
        raise ValueError("Résumé des fournisseurs absent")
    return sha, doc


def convert_report(doc: dict, sha: str) -> dict:
    """Pure transformation: candidates + their own editions/ISBN, no matching.

    A search result without full detail is retained as a work suggestion;
    never inherit bibliographic editions from another candidate/source.
    """
    if not SHA_RE.fullmatch(sha):
        raise ValueError("SHA-256 invalide")
    works, editions, volumes = [], [], []
    dedup: set[tuple[int, str, str]] = set()
    for pos, item in enumerate(doc["entries"], 1):
        if not isinstance(item, dict) or not isinstance(item.get("sources"), dict):
            raise ValueError("Entrée V2 malformée")
        origin = item.get("origin")
        if origin not in ("pending", "owned", "catalog"):
            raise ValueError("Segment d'origine inconnu")
        expected_market = "FR_PRINT" if origin != "catalog" else "INTERNATIONAL"
        market = item.get("market_target", expected_market)
        if market != expected_market:
            raise ValueError("Cible de marché incohérente avec l'origine")
        title = clean(item.get("title"))
        if not title:
            raise ValueError("Titre source manquant")
        for source in PROVIDERS:
            sr = item["sources"].get(source)
            if not isinstance(sr, dict):
                continue
            status = clean(sr.get("status"), 50)
            searches = sr.get("candidates") or []
            if not isinstance(searches, list):
                raise ValueError("Liste de candidats invalide")
            details_by_id = {}
            if isinstance(sr.get("details"), dict) and sr.get("selected_id"):
                details_by_id[str(sr["selected_id"])] = (sr["details"], "OK")
            for competitor in sr.get("competing_details") or []:
                if not isinstance(competitor, dict):
                    continue
                ext = clean(competitor.get("id"), 30)
                if ext and isinstance(competitor.get("details"), dict) and competitor.get("status") == "OK":
                    details_by_id[ext] = (competitor["details"], "OK")
            review = sr.get("matching_review") or {}
            review = review if isinstance(review, dict) else {}
            competing_scores = {}
            for r in review.get("competing_evidence") or []:
                if isinstance(r, dict) and r.get("id"):
                    competing_scores[str(r["id"])] = r
            for candidate in searches[:16]:
                if not isinstance(candidate, dict):
                    continue
                external = clean(candidate.get("id"), 30)
                candidate_title = clean(candidate.get("title"))
                evidence = candidate.get("evidence")
                if (not re.fullmatch(r"[1-9]\d{0,14}", external) or
                        not candidate_title or evidence not in
                        ("EXACT_TITLE", "SAME_MAL_ID", "SUGGESTION_ONLY")):
                    continue
                key = (pos, source, external)
                if key in dedup:
                    continue
                dedup.add(key)
                detail, detail_status = details_by_id.get(external, ({}, "NOT_AVAILABLE"))
                side = competing_scores.get(external, {})
                principal = str(sr.get("selected_id") or "") == external
                score_review = side if side else review if principal else {}
                wscore = (score_review.get("work") or {}).get("score") if isinstance(score_review, dict) else None
                escore = (score_review.get("edition") or {}).get("score") if isinstance(score_review, dict) else None
                wscore = wscore if isinstance(wscore, int) and 0 <= wscore <= 100 else None
                escore = escore if isinstance(escore, int) and 0 <= escore <= 100 else None
                decl = strings(review.get("edition_targets"), maximum=12)
                work = {
                    "sha": sha, "position": pos, "input_title": title,
                    "origin": origin, "market_target": market,
                    "provider": source, "external_id": external,
                    "title": candidate_title,
                    "work_type": clean(detail.get("work_type") or candidate.get("format"), 60),
                    "evidence": evidence, "search_status": status,
                    "detail_status": detail_status, "work_score": wscore,
                    "edition_score": escore, "authors": strings(detail.get("authors")),
                    "publishers": strings(detail.get("publishers")),
                    "genres": strings(detail.get("genres")),
                    "themes": strings(detail.get("themes")),
                    "aliases": strings(detail.get("aliases")),
                    "edition_declarations": decl,
                    "reference_count": detail.get("volume_items_seen")
                    if isinstance(detail.get("volume_items_seen"), int) and
                       detail["volume_items_seen"] >= 0 else None,
                    "reference_truncated": bool(detail.get("book_references_truncated"))
                }
                works.append(work)
                for edition in detail.get("editions") or []:
                    if not isinstance(edition, dict):
                        continue
                    lang = clean(edition.get("lang"), 20).lower()
                    medium = clean(edition.get("medium"), 20).lower()
                    label = clean(edition.get("edition"), 90).lower()
                    count = edition.get("volume_count")
                    count = count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None
                    if lang and medium and label:
                        editions.append((key, lang, medium, label, count))
                for volume in detail.get("book_references") or []:
                    if not isinstance(volume, dict):
                        continue
                    code = volume.get("isbn13")
                    valid = isbn13(str(code)) if isinstance(code, (str, int)) else None
                    if not valid:
                        continue
                    lang = clean(volume.get("lang"), 20).lower()
                    medium = clean(volume.get("medium"), 20).lower()
                    edition = clean(volume.get("edition_label"), 90).lower()
                    number = clean(volume.get("volume_label"), 40)
                    date = clean(volume.get("released_on"), 32)
                    if lang and medium:
                        volumes.append((key, valid, lang, medium, edition, number, date))
    return {"works": works, "editions": editions, "volumes": volumes,
            "entries": len(doc["entries"]),
            "source_sha256": sha,
            "generated_at": clean(doc.get("generated_at"), 70)}


def _volume_number(label: str) -> int | None:
    """Tome numbers require explicit wording or a short bare integer."""
    number = volume_from_title(label)
    if number is not None:
        return number
    value = label.strip()
    if re.fullmatch(r"0*[1-9][0-9]{0,2}", value):
        return int(value)
    return None


def isbn_staging_conflicts(stage: dict) -> dict:
    """Report contradictory FR print ISBN claims without merging source works.

    These are source *candidates*: a repeated ISBN across two series or two
    explicit edition families is a manual-review signal, not a valid link.
    Private inventory titles are never included in the diagnostic rows.
    """
    by_isbn: dict[str, list[tuple]] = defaultdict(list)
    for key, isbn, lang, medium, label, volume, _ in stage["volumes"]:
        if lang == "fr" and medium == "print":
            by_isbn[isbn].append((key, edition_family(label),
                                  _volume_number(volume)))
    conflicts = []
    for code, sources in sorted(by_isbn.items()):
        families = sorted({fam for _, fam, _ in sources if fam})
        tomes = sorted({n for _, _, n in sources if n is not None})
        origins = {key[0] for key, _, _ in sources}
        if len(origins) > 1:
            reason = "COMPETING_INPUT_WORKS"
        elif len(families) > 1:
            reason = "CONFLICTING_EDITION_FAMILIES"
        elif len(tomes) > 1:
            reason = "CONFLICTING_TOME_NUMBERS"
        else:
            continue
        conflicts.append({
            "isbn13": code, "reason": reason,
            "edition_families": families, "tome_numbers": tomes,
            "source_candidates": [
                {"provider": key[1], "external_id": key[2]}
                for key in sorted({entry[0] for entry in sources})
            ],
            "registration_ready": False,
        })
    return {
        "isbn_conflict_count": len(conflicts),
        "isbn_conflicts_sample": conflicts[:20],
        "isbn_conflict_sample_truncated": len(conflicts) > 20,
    }


def preview_summary(stage: dict) -> dict:
    works, volumes = stage["works"], stage["volumes"]
    fr_books = [row for row in volumes if row[2] == "fr" and row[3] == "print"]
    counts = Counter(x["provider"] for x in works)
    return {
        "report_sha256": stage["source_sha256"],
        "entries": stage["entries"],
        "work_candidates": len(works),
        "by_provider": dict(counts),
        "editions": len(stage["editions"]), "isbn_evidence": len(volumes),
        "french_print_isbn_evidence": len(fr_books),
        "missing_details": sum(x["detail_status"] != "OK" for x in works),
        "incomplete_volume_lists": sum(x["reference_truncated"] for x in works),
        "decision": "REVIEW_REQUIRED",
        "canonical_mutations": 0,
        "ownership_mutations": 0,
        **isbn_staging_conflicts(stage),
    }


def save_preview(stage: dict, directory: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    sha = stage["source_sha256"][:12]
    js = directory / f"preparation_{sha}.json"
    cs = directory / f"candidats_{sha}.csv"
    summary = preview_summary(stage)
    js.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    edition_keys = {key for key, *_ in stage["editions"]}
    books = Counter(key for key, *_ in stage["volumes"])
    with cs.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["manga_entree","origine","marche_cible","source","id_source",
                         "candidat","type_oeuvre","etat_recherche","titre_preuve",
                         "fiche","score_oeuvre_indicatif","score_edition_indicatif",
                         "editions_documentees","isbn_reference_count",
                         "liste_volumes_partielle","decision"])
        for w in stage["works"]:
            key = (w["position"], w["provider"], w["external_id"])
            writer.writerow([w["input_title"], w["origin"], w["market_target"],
                             w["provider"], w["external_id"], w["title"], w["work_type"],
                             w["search_status"], w["evidence"], w["detail_status"],
                             w["work_score"], w["edition_score"], key in edition_keys,
                             books[key], w["reference_truncated"], "REVIEW_REQUIRED"])
    return js, cs


def import_stage(db: Any, stage: dict, *, report_file: str) -> dict:
    """One atomic transaction, replay-safe by SHA, no writes to canonical tables."""
    with db.transaction():
        with db.cursor() as cur:
            cur.execute(DDL)
            cur.execute("SELECT source_sha256 FROM bib_stage_batch WHERE source_sha256=%s",
                        (stage["source_sha256"],))
            if cur.fetchone():
                return {"status": "ALREADY_PREPARED", **preview_summary(stage)}
            cur.execute(
                """INSERT INTO bib_stage_batch
                   (source_sha256,report_file,generated_at,entry_count)
                   VALUES (%s,%s,%s,%s)""",
                (stage["source_sha256"], report_file[:200],
                 stage["generated_at"], stage["entries"]))
            lookup: dict[tuple[int, str, str], int] = {}
            for work in stage["works"]:
                cur.execute(CANDIDATE_INSERT, work)
                result = cur.fetchone()
                candidate_id = result["id"] if isinstance(result, dict) else result[0]
                lookup[(work["position"], work["provider"], work["external_id"])] = candidate_id
            for key, lang, medium, edition, count in stage["editions"]:
                cur.execute(EDITION_INSERT, (lookup[key], lang, medium, edition, count))
            for key, isbn, lang, medium, edition, number, released in stage["volumes"]:
                cur.execute(VOLUME_INSERT, (
                    lookup[key], isbn, lang, medium, edition, number, released))
    return {"status": "PREPARED_FOR_REVIEW", **preview_summary(stage)}


def bnf_crosscheck(db: Any, stage: dict) -> dict:
    """Read-only BnF ISBN crosscheck; NEVER resolves work or edition identity."""
    isbn_list = sorted({code for _, code, lang, medium, *_ in stage["volumes"]
                        if lang == "fr" and medium == "print"})
    if not isbn_list:
        return {"status": "NO_FRENCH_PRINT_ISBN_IN_REPORT", "matches": 0}
    with db.cursor() as cur:
        cur.execute("SELECT to_regclass('public.bnf_bulk_notice') AS tbl")
        row = cur.fetchone()
        registered = row["tbl"] if isinstance(row, dict) else row[0]
        if registered is None:
            return {"status": "BNF_BULK_STAGING_NOT_LOADED", "matches": 0}
        cur.execute(
            """SELECT COUNT(*) AS n FROM bnf_bulk_notice
               WHERE isbn13 && %s::TEXT[]""", (isbn_list,))
        row = cur.fetchone()
        return {"status": "ISBN_BIBLIOGRAPHIC_CROSSCHECK_ONLY",
                "matches": row["n"] if isinstance(row, dict) else row[0],
                "isbn_checked": len(isbn_list),
                "ownership_verified": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zone bibliographique de préparation, sans fusion automatique")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--import", dest="do_import", action="store_true")
    mode.add_argument("--status", action="store_true")
    parser.add_argument("--report", help="Nom du fichier comparatif_sources_v2_....json (pas de chemin)")
    args = parser.parse_args(argv)
    if args.status:
        with get_postgres_connection() as db, db.cursor() as cur:
            cur.execute("SELECT to_regclass('public.bib_stage_batch') AS tbl")
            if not cur.fetchone()["tbl"]:
                print("Aucun lot de staging bibliographique enregistré.")
                return 0
            cur.execute("""SELECT source_sha256,report_file,entry_count,imported_at
                           FROM bib_stage_batch ORDER BY imported_at DESC LIMIT 10""")
            for row in cur.fetchall():
                print(json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False))
        return 0
    path = select_report(args.report)
    sha, report = read_report(path)
    stage = convert_report(report, sha)
    paths = save_preview(stage)
    print(json.dumps(preview_summary(stage), ensure_ascii=False))
    print("Aperçu local :", paths[0], paths[1])
    print("Aucune recherche Internet ni aucun rapprochement automatique.")
    if args.preview:
        return 0
    with get_postgres_connection() as db:
        result = import_stage(db, stage, report_file=path.name)
        check = bnf_crosscheck(db, stage)
    print(json.dumps({"staging": result, "bnf": check}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("Staging bibliographique refusé :", str(exc), file=sys.stderr)
        raise SystemExit(2)
