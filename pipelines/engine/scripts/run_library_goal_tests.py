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
REPORT_PATH = REPORT_DIR / "library_goal_tests_v0_8_3.md"


MIXED_LIBRARY_ITEMS: list[dict[str, Any]] = [
    {"title": "Naruto", "status": "READ", "score": 8.0, "favorite": False},
    {"title": "Death Note", "status": "READ", "score": 9.0, "favorite": True},
    {"title": "Fullmetal Alchemist", "status": "READ", "score": 9.0, "favorite": True},
    {"title": "Nana", "status": "READ", "score": 8.5, "favorite": False},
]


GOALS: list[dict[str, str]] = [
    {
        "code": "SIMILAR_SAFE",
        "label": "Proche de mes goûts",
        "description": "Recommandations proches des goûts dominants de la bibliothèque.",
    },
    {
        "code": "READ_NEXT",
        "label": "Quoi lire ensuite",
        "description": "Recommandations pratiques à lire maintenant, avec bonus qualité/statut/popularité.",
    },
    {
        "code": "SHORT_FINISHED",
        "label": "Série terminée / plutôt courte",
        "description": "Recommandations terminées, avec préférence pour les séries courtes ou moyennes.",
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


def get_library_recommendations(goal: str, limit: int = 5) -> dict[str, Any]:
    return api_post(
        "/recommendations/library",
        payload={
            "limit": limit,
            "min_score": 6.8,
            "only_finished": False,
            "exclude_sensitive_mismatches": False,
            "recommendation_goal": goal,
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


def format_list(values: list[str] | None) -> str:
    if not values:
        return ""

    return ", ".join(values)


def main() -> int:
    if "--reset-library" not in sys.argv:
        print("ERREUR : ce script vide la bibliothèque locale avant le test.")
        print("Relance avec :")
        print("  python pipelines\\engine\\scripts\\run_library_goal_tests.py --reset-library")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Mangadvisor - Tests objectifs recommandations")
    print("==================================================")
    print(f"API : {API_BASE_URL}")
    print()

    clear_library()

    added_items: list[dict[str, Any]] = []

    for spec in MIXED_LIBRARY_ITEMS:
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

    goal_results: list[dict[str, Any]] = []

    for goal in GOALS:
        goal_code = goal["code"]

        print(f"Test objectif : {goal_code}")

        result = get_library_recommendations(goal=goal_code, limit=5)
        recommendations = result.get("recommendations", [])

        goal_results.append(
            {
                "goal": goal,
                "result": result,
                "recommendations": recommendations,
            }
        )

        print(
            "Reco : "
            + ", ".join([recommendation.get("title", "") for recommendation in recommendations])
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "# Mangadvisor — Tests objectifs recommandations bibliothèque V0.8.3",
        "",
        f"Date d’exécution : `{now}`",
        "",
        f"API testée : `{API_BASE_URL}`",
        "",
        "## Bibliothèque de test",
        "",
        "| Demandé | Trouvé | Statut | Note | Favori |",
        "|---|---|---|---:|---|",
    ]

    for item in added_items:
        lines.append(
            "| "
            f"{md_cell(item['requested_title'])} | "
            f"{md_cell(item['matched_title'])} | "
            f"{md_cell(item['status'])} | "
            f"{format_score(item['score'])} | "
            f"{'Oui' if item['favorite'] else 'Non'} |"
        )

    lines.extend(
        [
            "",
            "## Comparaison synthétique",
            "",
            "| Objectif | Recommandations obtenues |",
            "|---|---|",
        ]
    )

    for entry in goal_results:
        goal = entry["goal"]
        recommendations = entry["recommendations"]
        titles = [recommendation.get("title", "") for recommendation in recommendations]

        lines.append(
            "| "
            f"{md_cell(goal['label'])} | "
            f"{md_cell(', '.join(titles))} |"
        )

    lines.extend(
        [
            "",
            "## Détail par objectif",
            "",
        ]
    )

    for entry in goal_results:
        goal = entry["goal"]
        result = entry["result"]
        recommendations = entry["recommendations"]
        profile_summary = result.get("profile_summary") or {}
        positive_sources = result.get("positive_sources") or []

        lines.extend(
            [
                f"## {goal['label']} — `{goal['code']}`",
                "",
                f"**Description :** {goal['description']}",
                "",
                f"**Objectif retourné par l’API :** `{result.get('recommendation_goal')}`",
                "",
                "### Sources utilisées",
                "",
                "| Titre | Statut bibliothèque | Note | Favori | Poids positif |",
                "|---|---|---:|---|---:|",
            ]
        )

        for source in positive_sources:
            lines.append(
                "| "
                f"{md_cell(source.get('title'))} | "
                f"{md_cell(source.get('library_status'))} | "
                f"{format_score(source.get('user_score'))} | "
                f"{'Oui' if source.get('is_favorite') else 'Non'} | "
                f"{format_score(source.get('positive_weight'))} |"
            )

        lines.extend(
            [
                "",
                "### Profil détecté",
                "",
                f"**Règle de sélection :** {profile_summary.get('source_selection_rule', 'Non renseignée')}",
                "",
                "#### Top genres",
                "",
                "| Genre | Sources | Poids |",
                "|---|---:|---:|",
            ]
        )

        for item in (profile_summary.get("top_genres") or [])[:8]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )

        lines.extend(
            [
                "",
                "#### Top thèmes",
                "",
                "| Thème | Sources | Poids |",
                "|---|---:|---:|",
            ]
        )

        for item in (profile_summary.get("top_themes") or [])[:8]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )

        lines.extend(
            [
                "",
                "#### Top cibles éditoriales",
                "",
                "| Cible | Sources | Poids |",
                "|---|---:|---:|",
            ]
        )

        for item in (profile_summary.get("top_demographics") or [])[:8]:
            lines.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )

        lines.extend(
            [
                "",
                "### Recommandations",
                "",
                "| Rang | Titre | Score final | Score base | Bonus objectif | Volumes | Chapitres | Statut | Genres communs | Thèmes communs | Cible commune |",
                "|---:|---|---:|---:|---:|---:|---:|---|---|---|---|",
            ]
        )

        for index, recommendation in enumerate(recommendations, start=1):
            lines.append(
                "| "
                f"{index} | "
                f"{md_cell(recommendation.get('title'))} | "
                f"{format_score(recommendation.get('recommendation_score'))} | "
                f"{format_score(recommendation.get('base_recommendation_score'))} | "
                f"{format_score(recommendation.get('goal_bonus'))} | "
                f"{md_cell(recommendation.get('volumes'))} | "
                f"{md_cell(recommendation.get('chapters'))} | "
                f"{md_cell(recommendation.get('status'))} | "
                f"{md_cell(format_list(recommendation.get('common_genres')))} | "
                f"{md_cell(format_list(recommendation.get('common_themes')))} | "
                f"{md_cell(format_list(recommendation.get('common_demographics')))} |"
            )

        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "Ce rapport compare les objectifs `SIMILAR_SAFE`, `READ_NEXT` et `SHORT_FINISHED` sur une bibliothèque volontairement mixte.",
            "Il permet de vérifier si l’objectif modifie réellement le classement final sans modifier le moteur V0.7.4.",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("==================================================")
    print("Tests terminés")
    print(f"Rapport généré : {REPORT_PATH}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())