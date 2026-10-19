"""PRIVATE / READ-ONLY real-collection test against the local Mangadvisor API.

Use the inventory CSV exported from the user's own spreadsheet under
data/private/. Never include it in commits, fixtures, logs or HTTP calls to
non-local hosts. No writes to PostgreSQL: /mangas search and /advisor/message
are both read-only, even though the latter uses POST for query parameters.

The goal is factual evaluation, NOT importing/read-rating the collection.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "collection", "tomes_principaux", "doublons_identiques",
    "autres_editions_a_identifier", "etat_releve",
}
FIELDS = (
    "collection", "tomes_principaux", "doublons_identiques",
    "autres_editions_a_identifier", "total_physique_estime",
    "etat_releve", "priorite_acces", "notes",
)
AUDIT_MESSAGES = (
    "Je veux un manga d'action, sans horreur et sans gore",
    "Je cherche un mystère terminé, idéalement en français",
    "Surprends-moi selon mes goûts",
)


def normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    return " ".join(folded.split())


def work_title(title: str) -> str:
    """Remove *only* explicit volume-count parentheticals, not series subtitles.

    This permits both 'Dragon Ball (34 tomes)' and '(42 tomes)' to be
    examined as possible editions of one work, without silently conflating
    their physical quantities or claiming a verified catalogue ID.
    """
    return re.sub(r"\s*\(\s*\d+\s+tomes?\s*\)\s*$", "", title, flags=re.I).strip()


def read_inventory(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            raise ValueError("CSV inventaire incorrect : colonnes requises absentes.")
        rows: list[dict[str, Any]] = []
        for position, row in enumerate(reader, start=2):
            title = (row.get("collection") or "").strip()
            if not title:
                continue
            parsed: dict[str, Any] = dict(row)
            parsed["collection"] = title
            for col in ("tomes_principaux", "doublons_identiques",
                        "autres_editions_a_identifier"):
                raw = (row.get(col) or "").strip()
                if not raw.isdecimal():
                    raise ValueError(f"Ligne {position} : nombre non valide dans {col}.")
                parsed[col] = int(raw)
            expected = sum(parsed[col] for col in (
                "tomes_principaux", "doublons_identiques",
                "autres_editions_a_identifier",
            ))
            if row.get("total_physique_estime"):
                if str(expected) != row["total_physique_estime"].strip():
                    raise ValueError(
                        f"Ligne {position} : total physique non cohérent."
                    )
            parsed["total_physique_estime"] = expected
            rows.append(parsed)
    if not rows:
        raise ValueError("Inventaire vide.")
    if len({x["collection"].casefold() for x in rows}) != len(rows):
        raise ValueError("Doublon exact de libellé : corriger l'inventaire.")
    return rows


def classify(title: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Conservative exact label matching. No guessed MAL IDs or ISBNs."""
    target = normalized(work_title(title))
    matches = []
    for item in candidates:
        labels = (
            item.get("title"), item.get("title_english"),
            item.get("title_japanese"),
        )
        if any(normalized(label) == target for label in labels
               if isinstance(label, str) and label):
            try:
                manga_id = int(item["id"])
            except (KeyError, TypeError, ValueError):
                continue
            if manga_id > 0 and manga_id not in [m["id"] for m in matches]:
                matches.append({"id": manga_id, "title": item.get("title")})
    if len(matches) == 1:
        return {"status": "label_exact_unique", "catalogue_id": matches[0]["id"],
                "catalogue_title": matches[0]["title"],
                "notes": "Titre exact parmi les libellés du catalogue ; édition/ISBN non vérifiés."}
    if len(matches) > 1:
        return {"status": "ambiguous", "catalogue_id": None,
                "catalogue_title": None,
                "notes": "Plusieurs œuvres possèdent ce titre : rapprochement manuel nécessaire.",
                "candidates": matches[:5]}
    return {"status": "manual_check", "catalogue_id": None,
            "catalogue_title": None,
            "notes": "Aucun titre exactement identique ; ne pas forcer un rapprochement.",
            "candidates": [
                {"id": c.get("id"), "title": c.get("title")}
                for c in candidates[:5]
            ]}


def assert_local_api(endpoint: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    if (parsed.scheme != "http" or parsed.hostname not in
            {"localhost", "127.0.0.1", "api"} or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or (parsed.path and parsed.path != "/")):
        raise ValueError(
            "Audit privé : seule l'API HTTP locale localhost/127.0.0.1/api est acceptée."
        )
    return endpoint.rstrip("/")


def fetch(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    method = "GET"
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, headers=headers, data=body, method=method)
    with urllib.request.urlopen(request, timeout=25) as response:
        obj = json.load(response)
    if not isinstance(obj, dict):
        raise ValueError("La réponse de l'API n'est pas un objet JSON.")
    return obj


def run(rows: list[dict[str, Any]], api: str, offline: bool = False) -> dict[str, Any]:
    summary = {
        "mode": "offline_inventory_only" if offline else "read_only_local_api",
        "inventory_rows": len(rows),
        "tomes_principaux": sum(r["tomes_principaux"] for r in rows),
        "doublons_identiques": sum(r["doublons_identiques"] for r in rows),
        "autres_editions_a_identifier": sum(
            r["autres_editions_a_identifier"] for r in rows
        ),
        "physical_total_estimate": sum(
            r["total_physique_estime"] for r in rows
        ),
        "reading_status_available": False,
        "isbn_identifiers_available": False,
        "ratings_available": False,
        "caution": (
            "Statuts d'inventaire, pas des notes ni des lectures confirmées ; "
            "ce test n'importe et ne modifie aucune donnée personnelle."
        ),
    }
    output: dict[str, Any] = {
        "metadata": summary,
        "catalogue_coverage": None,
        "recommendation_checks": [],
        "items": [],
    }
    if offline:
        return output
    base = assert_local_api(api)
    distinct_catalogue_ids: set[int] = set()
    statuses: Counter[str] = Counter()
    for index, item in enumerate(rows, start=1):
        title = item["collection"]
        term = work_title(title)
        url = base + "/mangas?" + urllib.parse.urlencode({
            "q": term, "limit": 70,
        })
        response = fetch(url)
        candidates = response.get("items")
        if not isinstance(candidates, list):
            raise ValueError("API /mangas : items absent.")
        match = classify(title, candidates)
        statuses[match["status"]] += 1
        if match["catalogue_id"] is not None:
            distinct_catalogue_ids.add(match["catalogue_id"])
        output["items"].append({
            "collection": title,
            "tomes_principaux": item["tomes_principaux"],
            "doublons_identiques": item["doublons_identiques"],
            "autres_editions_a_identifier": item["autres_editions_a_identifier"],
            **match,
        })
        if index % 25 == 0 or index == len(rows):
            print(f"Correspondances catalogue : {index}/{len(rows)} examinées.",
                  flush=True)
    output["catalogue_coverage"] = {
        "exact_unique_entries": statuses["label_exact_unique"],
        "ambiguous_entries": statuses["ambiguous"],
        "manual_check_entries": statuses["manual_check"],
        "distinct_confirmed_catalogue_ids": len(distinct_catalogue_ids),
        "source": "catalogue_labels_only",
        "edition_identification_confirmed": False,
    }
    for message in AUDIT_MESSAGES:
        payload = {
            "message": message, "context": {}, "lang": "fr", "limit": 12,
        }
        response = fetch(base + "/advisor/message", payload)
        recommended = response.get("recommendations", [])
        if not isinstance(recommended, list):
            raise ValueError("API du conseiller : liste de résultats absente.")
        all_ids = [int(r["id"]) for r in recommended]
        known_hits = [
            {"id": int(r["id"]), "title": r.get("title")}
            for r in recommended if int(r["id"]) in distinct_catalogue_ids
        ]
        q = response.get("quality_diagnostic") or {}
        output["recommendation_checks"].append({
            "message": message,
            "status": response.get("status"),
            "returned_count": len(recommended),
            "duplicate_ids_in_response": len(all_ids) - len(set(all_ids)),
            "listed_owned_titles_suggested": known_hits,
            "possible_collection_sync_issue": bool(known_hits),
            "note": (
                "Un titre figurant dans l'inventaire externe peut réapparaître "
                "si la bibliothèque de l'application n'a pas été synchronisée. "
                "Une correspondance de titre ne prouve pas l'identité de l'édition."
            ),
            "diagnostic": {
                "unique_recorded_tags": q.get("unique_recorded_tags"),
                "affinity_evidence_count": q.get("affinity_evidence_count"),
                "mean_pairwise_tag_overlap": q.get(
                    "mean_pairwise_tag_overlap"
                ),
            },
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True, type=Path,
                        help="CSV privé (ne jamais versionner).")
    parser.add_argument("--report",required=True, type=Path,
                        help="Chemin de sortie JSON, idéalement data/private/.")
    parser.add_argument("--api",default="http://127.0.0.1:8000")
    parser.add_argument("--offline",action="store_true",
                        help="Valider l'inventaire sans API ni base.")
    args = parser.parse_args()
    if not args.offline:
        assert_local_api(args.api)
    records = read_inventory(args.input)
    try:
        result = run(records, args.api, offline=args.offline)
    except (urllib.error.URLError, TimeoutError) as err:
        raise SystemExit(
            "API Mangadvisor locale inaccessible : démarrer Docker et l'option 3, "
            f"puis réessayer. Détail : {err}"
        ) from err
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(
        result, indent=2, ensure_ascii=False,
    ), encoding="utf-8")
    meta = result["metadata"]
    print(f"Inventaire valide : {meta['inventory_rows']} entrées, "
          f"{meta['physical_total_estimate']} volumes estimés.")
    if result["catalogue_coverage"]:
        print("Rapprochements de titres :",result["catalogue_coverage"])
        for check in result["recommendation_checks"]:
            print("Conseiller :",check["message"],"->",
                  check["returned_count"],"résultats ;",
                  len(check["listed_owned_titles_suggested"]),
                  "présents dans l'inventaire externe.")
    print("Rapport privé :", args.report)


if __name__ == "__main__":
    main()
