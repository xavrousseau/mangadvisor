from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


API_BASE_URL = os.getenv("MANGADVISOR_API_BASE_URL", "http://localhost:8000")
ROOT_DIR = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT_DIR / "docs" / "reports"
REPORT_PATH = REPORT_DIR / "library_import_robustness_tests_v0_8_11.md"


def api_request(
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{API_BASE_URL}{path}"

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erreur HTTP {exc.code} sur {method} {path}: {body}") from exc


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return api_request(path=path, method="GET", params=params)


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return api_request(path=path, method="POST", payload=payload)


def api_delete(path: str) -> dict[str, Any]:
    return api_request(path=path, method="DELETE")


def clear_library() -> None:
    data = api_get("/library", params={"limit": 500})

    for item in data.get("items", []):
        manga_id = item.get("manga_id")

        if manga_id:
            api_delete(f"/library/items/{manga_id}")


def import_csv_content(
    csv_content: str,
    delimiter: str = ",",
    dry_run: bool = False,
    default_status: str = "WANT_TO_READ",
) -> dict[str, Any]:
    return api_post(
        "/library/import/csv",
        payload={
            "csv_content": csv_content,
            "delimiter": delimiter,
            "default_status": default_status,
            "dry_run": dry_run,
        },
    )


def get_library_items() -> list[dict[str, Any]]:
    return api_get("/library", params={"limit": 500}).get("items", [])


def get_library_profile() -> dict[str, Any]:
    return api_get("/library/profile")


def build_csv(
    fieldnames: list[str],
    rows: list[dict[str, Any]],
    delimiter: str = ",",
) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def md_cell(value: Any) -> str:
    if value is None:
        return ""

    return str(value).replace("|", "\\|").replace("\n", " ")


def get_titles(items: list[dict[str, Any]]) -> list[str]:
    return sorted([item.get("title", "") for item in items])


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    clear_library()

    pre_import = case.get("pre_import")

    if pre_import:
        import_csv_content(
            csv_content=pre_import["csv_content"],
            delimiter=pre_import.get("delimiter", ","),
            dry_run=False,
            default_status=pre_import.get("default_status", "WANT_TO_READ"),
        )

    result = import_csv_content(
        csv_content=case["csv_content"],
        delimiter=case.get("delimiter", ","),
        dry_run=case.get("dry_run", False),
        default_status=case.get("default_status", "WANT_TO_READ"),
    )

    library_items = get_library_items()
    profile = get_library_profile()

    return {
        "case": case,
        "result": result,
        "library_items": library_items,
        "profile": profile,
    }


def evaluate_case(run_result: dict[str, Any]) -> str:
    case = run_result["case"]
    result = run_result["result"]
    library_items = run_result["library_items"]

    expected = case["expected"]

    checks = [
        result.get("matched_count") == expected.get("matched_count"),
        result.get("not_found_count") == expected.get("not_found_count"),
        result.get("error_count") == expected.get("error_count"),
        len(library_items) == expected.get("library_count"),
    ]

    expected_titles = expected.get("library_titles")

    if expected_titles is not None:
        checks.append(get_titles(library_items) == sorted(expected_titles))

    return "OK" if all(checks) else "KO"


def main() -> int:
    if "--reset-library" not in sys.argv:
        print("ERREUR : ce script vide la bibliothèque locale pendant les tests.")
        print("Relance avec :")
        print("  python pipelines\\engine\\scripts\\run_library_import_robustness_tests.py --reset-library")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    standard_fields = [
        "title",
        "library_status",
        "user_score",
        "is_favorite",
        "owned_volumes",
        "read_volumes",
        "notes",
    ]

    french_fields = [
        "titre",
        "statut",
        "note",
        "favori",
        "volumes_possedes",
        "volumes_lus",
        "commentaire",
    ]

    cases: list[dict[str, Any]] = [
        {
            "name": "Colonnes françaises + point-virgule + note avec virgule",
            "description": "Vérifie que titre/statut/note/favori et le séparateur ; sont bien reconnus.",
            "delimiter": ";",
            "csv_content": build_csv(
                french_fields,
                [
                    {
                        "titre": "Naruto",
                        "statut": "READ",
                        "note": "8,5",
                        "favori": "oui",
                        "volumes_possedes": "72",
                        "volumes_lus": "72",
                        "commentaire": "Import français",
                    },
                    {
                        "titre": "Bleach",
                        "statut": "READ",
                        "note": "8",
                        "favori": "non",
                        "volumes_possedes": "74",
                        "volumes_lus": "74",
                        "commentaire": "",
                    },
                ],
                delimiter=";",
            ),
            "expected": {
                "matched_count": 2,
                "not_found_count": 0,
                "error_count": 0,
                "library_count": 2,
                "library_titles": ["Naruto", "Bleach"],
            },
        },
        {
            "name": "Statut invalide",
            "description": "Vérifie qu'une ligne avec un statut inconnu part en erreur sans casser tout l'import.",
            "csv_content": build_csv(
                standard_fields,
                [
                    {
                        "title": "Naruto",
                        "library_status": "READ",
                        "user_score": "8.5",
                        "is_favorite": "true",
                        "owned_volumes": "",
                        "read_volumes": "",
                        "notes": "",
                    },
                    {
                        "title": "Bleach",
                        "library_status": "JAI_LU",
                        "user_score": "8",
                        "is_favorite": "false",
                        "owned_volumes": "",
                        "read_volumes": "",
                        "notes": "Statut invalide attendu",
                    },
                ],
            ),
            "expected": {
                "matched_count": 1,
                "not_found_count": 0,
                "error_count": 1,
                "library_count": 1,
                "library_titles": ["Naruto"],
            },
        },
        {
            "name": "Titre vide",
            "description": "Vérifie qu'une ligne sans titre part en erreur.",
            "csv_content": build_csv(
                standard_fields,
                [
                    {
                        "title": "",
                        "library_status": "READ",
                        "user_score": "7",
                        "is_favorite": "false",
                        "owned_volumes": "",
                        "read_volumes": "",
                        "notes": "Titre manquant",
                    },
                    {
                        "title": "Death Note",
                        "library_status": "READ",
                        "user_score": "9",
                        "is_favorite": "true",
                        "owned_volumes": "12",
                        "read_volumes": "12",
                        "notes": "",
                    },
                ],
            ),
            "expected": {
                "matched_count": 1,
                "not_found_count": 0,
                "error_count": 1,
                "library_count": 1,
                "library_titles": ["Death Note"],
            },
        },
        {
            "name": "Doublon dans le fichier",
            "description": "Vérifie qu'un doublon met à jour le même manga plutôt que de créer deux entrées.",
            "csv_content": build_csv(
                standard_fields,
                [
                    {
                        "title": "Naruto",
                        "library_status": "WANT_TO_READ",
                        "user_score": "",
                        "is_favorite": "false",
                        "owned_volumes": "",
                        "read_volumes": "",
                        "notes": "Première ligne",
                    },
                    {
                        "title": "Naruto",
                        "library_status": "READ",
                        "user_score": "8.5",
                        "is_favorite": "true",
                        "owned_volumes": "72",
                        "read_volumes": "72",
                        "notes": "Deuxième ligne prioritaire via upsert",
                    },
                ],
            ),
            "expected": {
                "matched_count": 2,
                "not_found_count": 0,
                "error_count": 0,
                "library_count": 1,
                "library_titles": ["Naruto"],
            },
        },
        {
            "name": "Mise à jour d'un manga déjà présent",
            "description": "Vérifie qu'un import met à jour un manga déjà en bibliothèque.",
            "pre_import": {
                "csv_content": build_csv(
                    standard_fields,
                    [
                        {
                            "title": "Naruto",
                            "library_status": "WANT_TO_READ",
                            "user_score": "",
                            "is_favorite": "false",
                            "owned_volumes": "",
                            "read_volumes": "",
                            "notes": "Avant mise à jour",
                        }
                    ],
                ),
            },
            "csv_content": build_csv(
                standard_fields,
                [
                    {
                        "title": "Naruto",
                        "library_status": "READ",
                        "user_score": "9",
                        "is_favorite": "true",
                        "owned_volumes": "72",
                        "read_volumes": "72",
                        "notes": "Après mise à jour",
                    }
                ],
            ),
            "expected": {
                "matched_count": 1,
                "not_found_count": 0,
                "error_count": 0,
                "library_count": 1,
                "library_titles": ["Naruto"],
            },
        },
        {
            "name": "Booléen invalide",
            "description": "Vérifie qu'une valeur favorite invalide part en erreur.",
            "csv_content": build_csv(
                standard_fields,
                [
                    {
                        "title": "Naruto",
                        "library_status": "READ",
                        "user_score": "8.5",
                        "is_favorite": "peut-être",
                        "owned_volumes": "",
                        "read_volumes": "",
                        "notes": "",
                    }
                ],
            ),
            "expected": {
                "matched_count": 0,
                "not_found_count": 0,
                "error_count": 1,
                "library_count": 0,
                "library_titles": [],
            },
        },
    ]

    print("==================================================")
    print("Mangadvisor - Tests robustesse import bibliotheque")
    print("==================================================")
    print(f"API : {API_BASE_URL}")
    print()

    results = []

    for case in cases:
        print(f"Test : {case['name']}")
        run_result = run_case(case)
        status = evaluate_case(run_result)
        run_result["status"] = status
        results.append(run_result)
        print(f"Résultat : {status}")
        print()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "# Mangadvisor — Tests robustesse import bibliothèque V0.8.11",
        "",
        f"Date d’exécution : `{now}`",
        "",
        f"API testée : `{API_BASE_URL}`",
        "",
        "## Synthèse",
        "",
        "| Test | Matched | Non trouvés | Erreurs | Taille bibliothèque | Résultat |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for run_result in results:
        result = run_result["result"]
        library_items = run_result["library_items"]

        lines.append(
            "| "
            f"{md_cell(run_result['case']['name'])} | "
            f"{result.get('matched_count', 0)} | "
            f"{result.get('not_found_count', 0)} | "
            f"{result.get('error_count', 0)} | "
            f"{len(library_items)} | "
            f"{run_result['status']} |"
        )

    lines.extend(["", "## Détail", ""])

    for run_result in results:
        case = run_result["case"]
        result = run_result["result"]
        library_items = run_result["library_items"]
        profile = run_result["profile"]

        lines.extend(
            [
                f"## {case['name']}",
                "",
                f"**Description :** {case['description']}",
                "",
                f"**Résultat :** `{run_result['status']}`",
                "",
                "### Import",
                "",
                f"- Matched : `{result.get('matched_count', 0)}`",
                f"- Non trouvés : `{result.get('not_found_count', 0)}`",
                f"- Erreurs : `{result.get('error_count', 0)}`",
                "",
                "### Lignes importées",
                "",
                "| Ligne | Demandé | Trouvé | Statut | Note | Favori |",
                "|---:|---|---|---|---:|---|",
            ]
        )

        for item in result.get("imported_items", []):
            lines.append(
                "| "
                f"{item.get('line')} | "
                f"{md_cell(item.get('requested_title'))} | "
                f"{md_cell(item.get('matched_title'))} | "
                f"{md_cell(item.get('library_status'))} | "
                f"{md_cell(item.get('user_score'))} | "
                f"{'Oui' if item.get('is_favorite') else 'Non'} |"
            )

        if not result.get("imported_items"):
            lines.append("|  | Aucun |  |  |  |  |")

        lines.extend(
            [
                "",
                "### Titres non trouvés",
                "",
                "| Ligne | Titre |",
                "|---:|---|",
            ]
        )

        for item in result.get("not_found_items", []):
            lines.append(
                "| "
                f"{item.get('line')} | "
                f"{md_cell(item.get('title'))} |"
            )

        if not result.get("not_found_items"):
            lines.append("|  | Aucun |")

        lines.extend(
            [
                "",
                "### Erreurs",
                "",
                "| Ligne | Erreur |",
                "|---:|---|",
            ]
        )

        for item in result.get("error_items", []):
            lines.append(
                "| "
                f"{item.get('line')} | "
                f"{md_cell(item.get('error'))} |"
            )

        if not result.get("error_items"):
            lines.append("|  | Aucune |")

        lines.extend(
            [
                "",
                "### Bibliothèque après test",
                "",
                "| Titre | Statut | Note | Favori |",
                "|---|---|---:|---|",
            ]
        )

        for item in library_items:
            lines.append(
                "| "
                f"{md_cell(item.get('title'))} | "
                f"{md_cell(item.get('library_status'))} | "
                f"{md_cell(item.get('user_score'))} | "
                f"{'Oui' if item.get('is_favorite') else 'Non'} |"
            )

        if not library_items:
            lines.append("| Bibliothèque vide |  |  |  |")

        lines.extend(
            [
                "",
                "### Profil après test",
                "",
                f"**Statuts :** `{profile.get('status_counts', {})}`",
                "",
                f"**Sources positives :** `{profile.get('positive_source_count', 0)}`",
                "",
                f"**Signaux négatifs :** `{profile.get('negative_item_count', 0)}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Note",
            "",
            "Ce test vérifie la robustesse de l'import bibliothèque : colonnes françaises, séparateur point-virgule, notes avec virgule, statuts invalides, titres vides, doublons, mises à jour et booléens invalides.",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("==================================================")
    print("Tests terminés")
    print(f"Rapport généré : {REPORT_PATH}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())