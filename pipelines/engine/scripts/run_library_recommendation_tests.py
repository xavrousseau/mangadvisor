from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


API_BASE_URL = os.getenv("MANGADVISOR_API_BASE_URL", "http://localhost:8000")
ROOT_DIR = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT_DIR / "docs" / "reports"
REPORT_PATH = REPORT_DIR / "library_recommendation_tests_v0_8_2_profile_summary.md"


SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Bibliothèque shōnen aventure",
        "description": "Utilisateur fan de shōnen d'aventure, combats, progression et pouvoirs.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
        ],
    },
    {
        "name": "Bibliothèque thriller psychologique",
        "description": "Utilisateur attiré par les intrigues, manipulations et mystères.",
        "items": [
            {"title": "Death Note", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "Monster", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "20th Century Boys", "status": "READ", "score": 8.5, "favorite": False},
        ],
    },
    {
        "name": "Bibliothèque seinen sombre",
        "description": "Utilisateur attiré par les univers sombres, violents et matures.",
        "items": [
            {"title": "Berserk", "status": "READ", "score": 9.5, "favorite": True},
            {"title": "Blame!", "status": "READ", "score": 8.5, "favorite": False},
            {"title": "Battle Royale", "status": "READ", "score": 8.0, "favorite": False},
        ],
    },
    {
        "name": "Bibliothèque tranche de vie contemplative",
        "description": "Utilisateur attiré par les ambiances calmes, poétiques et contemplatives.",
        "items": [
            {"title": "Mushishi", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "Yokohama Kaidashi Kikou", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "Natsume Yuujinchou", "status": "READING", "score": 8.5, "favorite": False},
        ],
    },
    {
        "name": "Bibliothèque mixte grand public",
        "description": "Utilisateur avec des goûts variés : action, thriller, émotion.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Death Note", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "Fullmetal Alchemist", "status": "READ", "score": 9.0, "favorite": True},
            {"title": "Nana", "status": "READ", "score": 8.5, "favorite": False},
        ],
    },
]


def normalize_text(value: str) -> str:
    value = value.strip()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = value.replace("☆", " ")
    value = value.replace("★", " ")
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def api_request(
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{API_BASE_URL}{path}"

    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erreur HTTP {exc.code} sur {method} {path}: {body}") from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Impossible d'appeler l'API {API_BASE_URL}. Vérifie que mangadvisor_api est lancé."
        ) from exc


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return api_request(path=path, method="GET", params=params)


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return api_request(path=path, method="POST", payload=payload)


def api_delete(path: str) -> dict[str, Any]:
    return api_request(path=path, method="DELETE")


def type_rank(manga_type: str | None) -> int:
    if manga_type == "Manga":
        return 0
    if manga_type in {"Manhwa", "Manhua"}:
        return 1
    if manga_type == "One-shot":
        return 2
    if manga_type == "Light Novel":
        return 5
    return 9


def find_manga(title: str) -> dict[str, Any]:
    data = api_get(
        "/mangas",
        params={
            "q": title,
            "limit": 100,
        },
    )

    items = data.get("items", [])

    if not items:
        raise RuntimeError(f"Manga introuvable : {title}")

    expected = normalize_text(title)

    def rank(item: dict[str, Any]) -> tuple[int, int, int, float, str]:
        title_values = [
            item.get("title") or "",
            item.get("title_english") or "",
            item.get("title_japanese") or "",
        ]

        normalized_values = [normalize_text(value) for value in title_values if value]

        if expected in normalized_values:
            match_rank = 0
        elif any(expected in value or value in expected for value in normalized_values):
            match_rank = 1
        else:
            match_rank = 9

        popularity = item.get("popularity")
        score = item.get("score")

        return (
            match_rank,
            type_rank(item.get("manga_type")),
            int(popularity) if popularity is not None else 999999,
            -float(score) if score is not None else 0.0,
            item.get("title") or "",
        )

    return sorted(items, key=rank)[0]


def clear_library() -> None:
    data = api_get(
        "/library",
        params={
            "limit": 500,
        },
    )

    items = data.get("items", [])

    for item in items:
        manga_id = item.get("manga_id")

        if manga_id:
            api_delete(f"/library/items/{manga_id}")


def add_library_item(manga: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "manga_id": manga["id"],
        "library_status": spec["status"],
        "user_score": spec.get("score"),
        "is_favorite": spec.get("favorite", False),
        "owned_volumes": spec.get("owned_volumes"),
        "read_volumes": spec.get("read_volumes"),
        "notes": spec.get("notes"),
        "started_at": None,
        "finished_at": None,
    }

    return api_post("/library/items", payload=payload)


def get_library_recommendations(limit: int = 5) -> dict[str, Any]:
    return api_post(
        "/recommendations/library",
        payload={
            "limit": limit,
            "min_score": 6.8,
            "only_finished": False,
            "exclude_sensitive_mismatches": False,
        },
    )


def md_cell(value: Any) -> str:
    if value is None:
        return ""

    return str(value).replace("|", "\\|").replace("\n", " ")


def format_score(value: Any) -> str:
    if value is None:
        return ""

    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def format_profile_summary(profile_summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    if not profile_summary:
        return [
            "_Aucun résumé de profil retourné par l'API._",
            "",
        ]

    status_counts = profile_summary.get("status_counts") or {}
    top_genres = profile_summary.get("top_genres") or []
    top_themes = profile_summary.get("top_themes") or []
    top_demographics = profile_summary.get("top_demographics") or []

    lines.extend(
        [
            "### Résumé du profil bibliothèque interprété par l’API",
            "",
            f"**Règle de sélection des sources :** {profile_summary.get('source_selection_rule', 'Non renseignée')}",
            "",
            f"**Sources positives disponibles :** `{profile_summary.get('positive_source_count_available', 0)}`",
            "",
            f"**Sources positives utilisées :** `{profile_summary.get('positive_source_count_used', 0)}`",
            "",
            "#### Répartition par statut",
            "",
            "| Statut | Nombre |",
            "|---|---:|",
        ]
    )

    if status_counts:
        for status, count in sorted(status_counts.items()):
            lines.append(f"| {md_cell(status)} | {count} |")
    else:
        lines.append("| Aucun | 0 |")

    lines.extend(
        [
            "",
            "#### Top genres détectés",
            "",
            "| Genre | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_genres:
        for item in top_genres[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucun | 0 | 0 |")

    lines.extend(
        [
            "",
            "#### Top thèmes détectés",
            "",
            "| Thème | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_themes:
        for item in top_themes[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucun | 0 | 0 |")

    lines.extend(
        [
            "",
            "#### Top cibles éditoriales détectées",
            "",
            "| Cible | Sources | Poids total |",
            "|---|---:|---:|",
        ]
    )

    if top_demographics:
        for item in top_demographics[:10]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )
    else:
        lines.append("| Aucune | 0 | 0 |")

    lines.append("")

    return lines


def main() -> int:
    if "--reset-library" not in sys.argv:
        print("ERREUR : ce script vide la bibliothèque locale pour chaque scénario.")
        print("Relance avec :")
        print("  python pipelines\\engine\\scripts\\run_library_recommendation_tests.py --reset-library")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "# Mangadvisor — Tests recommandations depuis bibliothèque V0.8.2 — Profil enrichi",
        "",
        f"Date d’exécution : `{now}`",
        "",
        f"API testée : `{API_BASE_URL}`",
        "",
        "## Synthèse",
        "",
        "| Scénario | Sources bibliothèque | Recommandations obtenues |",
        "|---|---|---|",
    ]

    details: list[str] = []

    print("==================================================")
    print("Mangadvisor - Tests recommandations bibliothèque")
    print("==================================================")
    print(f"API : {API_BASE_URL}")
    print()

    for scenario in SCENARIOS:
        scenario_name = scenario["name"]
        print(f"Scénario : {scenario_name}")

        clear_library()

        added_items: list[dict[str, Any]] = []

        for spec in scenario["items"]:
            manga = find_manga(spec["title"])
            add_library_item(manga, spec)
            added_items.append(
                {
                    "requested_title": spec["title"],
                    "matched_title": manga.get("title"),
                    "manga_id": manga.get("id"),
                    "status": spec["status"],
                    "score": spec.get("score"),
                    "favorite": spec.get("favorite", False),
                }
            )

        result = get_library_recommendations(limit=5)
        recommendations = result.get("recommendations", [])
        positive_sources = result.get("positive_sources", [])
        positive_sources_available = result.get("positive_sources_available", [])
        profile_summary = result.get("profile_summary", {})

        source_titles = [source.get("title", "") for source in positive_sources]
        recommendation_titles = [reco.get("title", "") for reco in recommendations]

        lines.append(
            "| "
            f"{md_cell(scenario_name)} | "
            f"{md_cell(', '.join(source_titles))} | "
            f"{md_cell(', '.join(recommendation_titles))} |"
        )

        detail_rows = [
            f"## {scenario_name}",
            "",
            f"**Description :** {scenario['description']}",
            "",
            "### Bibliothèque chargée",
            "",
            "| Demandé | Trouvé | Statut | Note | Favori |",
            "|---|---|---|---:|---|",
        ]

        for item in added_items:
            detail_rows.append(
                "| "
                f"{md_cell(item['requested_title'])} | "
                f"{md_cell(item['matched_title'])} | "
                f"{md_cell(item['status'])} | "
                f"{format_score(item['score'])} | "
                f"{'Oui' if item['favorite'] else 'Non'} |"
            )

        detail_rows.extend(
            [
                "",
                "### Sources positives utilisées par l’API",
                "",
                "| Titre | Statut bibliothèque | Note | Favori | Poids positif |",
                "|---|---|---:|---|---:|",
            ]
        )

        for source in positive_sources:
            detail_rows.append(
                "| "
                f"{md_cell(source.get('title'))} | "
                f"{md_cell(source.get('library_status'))} | "
                f"{format_score(source.get('user_score'))} | "
                f"{'Oui' if source.get('is_favorite') else 'Non'} | "
                f"{format_score(source.get('positive_weight'))} |"
            )

        detail_rows.extend(
            [
                "",
                "### Sources positives disponibles",
                "",
                "| Titre | Statut bibliothèque | Note | Favori | Poids positif |",
                "|---|---|---:|---|---:|",
            ]
        )

        for source in positive_sources_available:
            detail_rows.append(
                "| "
                f"{md_cell(source.get('title'))} | "
                f"{md_cell(source.get('library_status'))} | "
                f"{format_score(source.get('user_score'))} | "
                f"{'Oui' if source.get('is_favorite') else 'Non'} | "
                f"{format_score(source.get('positive_weight'))} |"
            )

        detail_rows.extend([""])
        detail_rows.extend(format_profile_summary(profile_summary))

        detail_rows.extend(
            [
                "",
                "### Recommandations obtenues",
                "",
                "| Rang | Titre | Score reco | Score manga | Statut | Genres communs | Thèmes communs | Cible commune | Raison |",
                "|---:|---|---:|---:|---|---|---|---|---|",
            ]
        )

        for index, reco in enumerate(recommendations, start=1):
            detail_rows.append(
                "| "
                f"{index} | "
                f"{md_cell(reco.get('title'))} | "
                f"{format_score(reco.get('recommendation_score'))} | "
                f"{format_score(reco.get('score'))} | "
                f"{md_cell(reco.get('status'))} | "
                f"{md_cell(', '.join(reco.get('common_genres') or []))} | "
                f"{md_cell(', '.join(reco.get('common_themes') or []))} | "
                f"{md_cell(', '.join(reco.get('common_demographics') or []))} | "
                f"{md_cell(reco.get('reason'))} |"
            )

        detail_rows.extend(
            [
                "",
                f"**Mangas exclus car déjà en bibliothèque :** `{result.get('excluded_library_manga_count', 0)}`",
                "",
            ]
        )

        details.extend(detail_rows)

        print(f"Sources : {', '.join(source_titles)}")
        print(f"Reco    : {', '.join(recommendation_titles)}")
        print()

    lines.extend(
        [
            "",
            "## Détail des scénarios",
            "",
            *details,
            "",
            "## Note",
            "",
            "Ce rapport vérifie le comportement de `/recommendations/library` avec plusieurs bibliothèques types.",
            "Il sert à préparer l'amélioration de la pondération bibliothèque : favoris, notes, statuts négatifs, envies de lecture, etc.",
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