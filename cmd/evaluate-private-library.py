"""Local, READ-ONLY comparison of a private inventory CSV with running Mangadvisor.

No private manga title is committed to GitHub, sent to a cloud model or
written to the database. Only loopback API endpoints are accepted.
Input: the semicolon-separated CSV exported privately from the user's workbook.
Output: a PRIVATE local JSON/CSV report. Never automatically merge editions.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


def norm(s: object) -> str:
    text = unicodedata.normalize("NFKD", str(s or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def search_title(title: str) -> tuple[str, bool]:
    """Remove an explicit count used to distinguish physical formats ONLY for search."""
    clean = re.sub(r"\s*\(\s*\d+\s+tomes?\s*\)\s*$", "", title, flags=re.I)
    return clean, clean != title


def load_inventory(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        required = {
            "titre", "tomes_principaux_declares",
            "doublons_identiques_hors_profil", "autres_editions_non_identifiees",
        }
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("Colonnes manquantes dans le CSV Mangadvisor privé.")
        result = []
        for n, item in enumerate(reader, start=2):
            title = (item["titre"] or "").strip()
            if not title:
                raise ValueError(f"Sans titre en ligne {n}.")
            for key in required - {"titre"}:
                value = int(item[key])
                if value < 0:
                    raise ValueError(f"Quantité négative en ligne {n}.")
                item[key] = value
            result.append(item)
        if len({norm(item["titre"]) for item in result}) != len(result):
            raise ValueError("Des titres identiques apparaissent dans le fichier.")
        return result


def request_json(base: str, endpoint: str, payload: dict | None = None) -> dict:
    target = base + endpoint
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        target, data=body,
        method="POST" if body is not None else "GET",
        headers={"Content-Type":"application/json"},
    )
    with urlopen(req, timeout=25) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Réponse API inattendue.")
    return data


def match_catalog_entry(title: str, candidates: list[dict]) -> tuple[str, int | None, str]:
    """Conservative title reconciliation: NEVER guess an edition/series link."""
    searched, variant = search_title(title)
    target = norm(searched)
    exact = [
        item for item in candidates
        if any(norm(item.get(field)) == target for field in ("title", "title_english", "title_japanese"))
    ]
    unique = {item["id"]: item for item in exact if isinstance(item.get("id"), int)}
    if variant:
        return ("FORMAT_TO_VERIFY", None,
                ", ".join(str(item.get("title")) for item in unique.values())[:400])
    if len(unique) == 1:
        row = next(iter(unique.values()))
        return ("EXACT_TITLE", int(row["id"]), str(row.get("title") or ""))
    if len(unique) > 1:
        return ("AMBIGUOUS", None,
                ", ".join(str(item.get("title")) for item in unique.values())[:400])
    return ("TO_VERIFY" if candidates else "NOT_FOUND",
            None,
            ", ".join(str(item.get("title")) for item in candidates[:3])[:400])


def fetch_library(base: str) -> list[dict]:
    result = []
    for offset in range(0, 5000, 500):
        page = request_json(base, "/library?" + urlencode({"offset":offset,"limit":500}))
        items = page.get("items") or []
        if not isinstance(items, list):
            raise ValueError("Format bibliothèque API inattendu.")
        result.extend(items)
        if len(items) < 500:
            break
    return result


def analyze(base: str, inventory: list[dict]) -> tuple[dict, list[dict]]:
    request_json(base, "/health")
    current = fetch_library(base)
    current_ids = {r.get("manga_id") for r in current}
    rows: list[dict] = []
    reference_ids: set[int] = set()
    for record in inventory:
        title = record["titre"]
        searched, _ = search_title(title)
        response = request_json(base, "/mangas?" + urlencode({"q":searched,"limit":100}))
        entries = response.get("items") or []
        status, manga_id, match = match_catalog_entry(title, entries)
        if manga_id is not None:
            reference_ids.add(manga_id)
        rows.append({
            "titre":title,
            "tomes_principaux":record["tomes_principaux_declares"],
            "doublons_identiques":record["doublons_identiques_hors_profil"],
            "autres_editions_non_identifiees":record["autres_editions_non_identifiees"],
            "correspondance":status,
            "manga_id_valide":manga_id if manga_id is not None else "",
            "titre_candidat_catalogue":match,
            "present_dans_bibliotheque_app": (
                "OUI" if manga_id in current_ids else
                "NON" if manga_id is not None else "INDETERMINE"
            ),
        })
    queries = (
        "Je cherche un mystère, sans horreur et sans gore",
        "Je cherche un manga d'action ou d'aventure",
        "Surprends-moi selon mes goûts",
    )
    tests = []
    leaks = []
    for message in queries:
        reply = request_json(base, "/advisor/message", {
            "message":message,"context":{},"lang":"fr","limit":12,
        })
        suggestions = reply.get("recommendations") or []
        bad = [
            {"id":r.get("id"),"titre":r.get("title")}
            for r in suggestions if r.get("id") in reference_ids
        ]
        leaks.extend({"requete":message,**entry} for entry in bad)
        tests.append({
            "requete":message, "statut":reply.get("status"),
            "propositions":len(suggestions),
            "recoupements_certains_avec_inventaire":bad,
        })
    tally = dict(Counter(r["correspondance"] for r in rows))
    summary = {
        "verification_time_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"lecture seule, inventaire déclaré, sans ISBN ni notes de lecture",
        "series":len(inventory),
        "tomes_principaux":sum(r["tomes_principaux_declares"] for r in inventory),
        "doublons":sum(r["doublons_identiques_hors_profil"] for r in inventory),
        "autres_editions_a_verifier":sum(r["autres_editions_non_identifiees"] for r in inventory),
        "catalogue_correspondances":tally,
        "series_identifiees_catalogue":len(reference_ids),
        "series_identifiees_absentes_de_la_bibliotheque_app":sum(
            r["present_dans_bibliotheque_app"]=="NON" for r in rows
        ),
        "titre_possede_recommande_malgre_identifiant_confirme":leaks,
        "tests_conseiller":tests,
        "limits":[
            "Seuls les titres correspondants de façon unique et exacte sont validés.",
            "Un format tel que Dragon Ball (42 tomes) reste à vérifier manuellement.",
            "Une série absente de la bibliothèque applicative n'est pas importée.",
            "Les impressions de lecture, ISBN, numéros de tomes et éditions ne figurent pas dans l'inventaire.",
            "Une correspondance incertaine n'est jamais présentée comme une vraie exclusion vérifiée.",
            "L'exclusion de la bibliothèque applicative repose sur les titres déjà enregistrés dans l'application.",
        ],
    }
    return summary, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",required=True,type=Path,help="CSV PRIVÉ téléchargé depuis ChatGPT")
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    parser.add_argument("--out",type=Path,default=Path("private-evaluations"))
    args = parser.parse_args()
    endpoint = urlparse(args.url)
    if endpoint.scheme != "http" or endpoint.hostname not in {"localhost","127.0.0.1"}:
        parser.error("Seule l'API locale http://127.0.0.1 ou localhost est admise.")
    if endpoint.username or endpoint.password or endpoint.path not in ("","/"):
        parser.error("Adresse API locale invalide.")
    inventory = load_inventory(args.csv)
    try:
        report, rows = analyze(args.url.rstrip("/"), inventory)
    except (URLError, HTTPError, TimeoutError, ValueError) as exc:
        print(f"Erreur API: {exc}. Démarre d'abord Mangadvisor (option 3).",file=sys.stderr)
        return 1
    args.out.mkdir(parents=True,exist_ok=True)
    report_path=args.out/"rapport_collection_privee.json"
    table_path=args.out/"correspondances_collection_privee.csv"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    with table_path.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys(),delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{report['series']} entrées, {report['series_identifiees_catalogue']} associations exactes uniques.")
    print(f"{report['series_identifiees_absentes_de_la_bibliotheque_app']} associations vérifiées absentes de la bibliothèque applicative.")
    print(f"{len(report['titre_possede_recommande_malgre_identifiant_confirme'])} recoupement(s) entre titres déclarés et recommandations.")
    print(f"Rapports privés: {report_path} et {table_path}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
