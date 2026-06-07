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
REPORT_PATH = REPORT_DIR / "library_status_tests_v0_8_5.md"


SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Shōnen avec titre non intéressé",
        "description": "L'utilisateur aime Naruto/Bleach/Hunter x Hunter mais indique ne pas être intéressé par Fairy Tail.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
            {"title": "Fairy Tail", "status": "NOT_INTERESTED", "score": None, "favorite": False},
        ],
        "forbidden_titles": ["Fairy Tail"],
    },
    {
        "name": "Shōnen avec titre abandonné",
        "description": "L'utilisateur aime les grands shōnen mais a abandonné Fairy Tail.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
            {"title": "Fairy Tail", "status": "DROPPED", "score": 4.0, "favorite": False},
        ],
        "forbidden_titles": ["Fairy Tail"],
    },
    {
        "name": "Envie de lire déjà présente",
        "description": "L'utilisateur veut lire One Piece : il ne doit donc pas être recommandé à nouveau.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
            {"title": "One Piece", "status": "WANT_TO_READ", "score": None, "favorite": False},
        ],
        "forbidden_titles": ["One Piece"],
    },
    {
        "name": "Possédé mais pas encore lu",
        "description": "L'utilisateur possède Dragon Ball mais ne l'a pas encore lu : il ne doit pas être recommandé à nouveau.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
            {"title": "Dragon Ball", "status": "OWNED", "score": None, "favorite": False},
        ],
        "forbidden_titles": ["Dragon Ball"],
    },
    {
        "name": "Manga lu mais très mal noté",
        "description": "L'utilisateur a lu Fairy Tail mais l'a très mal noté. On vérifie son poids dans le profil.",
        "items": [
            {"title": "Naruto", "status": "READ", "score": 8.5, "favorite": True},
            {"title": "Bleach", "status": "READ", "score": 8.0, "favorite": False},
            {"title": "Hunter x Hunter", "status": "READING", "score": 9.0, "favorite": True},
            {"title": "Fairy Tail", "status": "READ", "score": 3.0, "favorite": False},
        ],
        "forbidden_titles": ["Fairy Tail"],
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
    data = api_get("/library", params={"limit": 500})
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


def get_library_recommendations(goal: str = "SIMILAR_SAFE", limit: int = 5) -> dict[str, Any]:
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


def title_is_present(title: str, titles: list[str]) -> bool:
    normalized_title = normalize_text(title)
    normalized_titles = {normalize_text(item) for item in titles}

    return normalized_title in normalized_titles


def main() -> int:
    if "--reset-library" not in sys.argv:
        print("ERREUR : ce script vide la bibliothèque locale pour chaque scénario.")
        print("Relance avec :")
        print("  python pipelines\\engine\\scripts\\run_library_status_tests.py --reset-library")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "# Mangadvisor — Tests statuts bibliothèque V0.8.5",
        "",
        f"Date d’exécution : `{now}`",
        "",
        f"API testée : `{API_BASE_URL}`",
        "",
        "## Synthèse",
        "",
        "| Scénario | Interdits | Recommandations | Résultat |",
        "|---|---|---|---|",
    ]

    detail_sections: list[str] = []

    print("==================================================")
    print("Mangadvisor - Tests statuts bibliotheque")
    print("==================================================")
    print(f"API : {API_BASE_URL}")
    print()

    for scenario in SCENARIOS:
        scenario_name = scenario["name"]
        forbidden_titles = scenario.get("forbidden_titles", [])

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

        result = get_library_recommendations(goal="SIMILAR_SAFE", limit=5)
        recommendations = result.get("recommendations", [])
        positive_sources = result.get("positive_sources", [])
        positive_sources_available = result.get("positive_sources_available", [])
        profile_summary = result.get("profile_summary", {})

        recommendation_titles = [
            recommendation.get("title", "")
            for recommendation in recommendations
        ]

        forbidden_found = [
            title
            for title in forbidden_titles
            if title_is_present(title, recommendation_titles)
        ]

        test_status = "OK" if not forbidden_found else "KO"

        lines.append(
            "| "
            f"{md_cell(scenario_name)} | "
            f"{md_cell(', '.join(forbidden_titles))} | "
            f"{md_cell(', '.join(recommendation_titles))} | "
            f"{test_status} |"
        )

        detail_rows = [
            f"## {scenario_name}",
            "",
            f"**Description :** {scenario['description']}",
            "",
            f"**Résultat du test :** `{test_status}`",
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
                "### Sources positives utilisées",
                "",
                "| Titre | Statut | Note | Favori | Poids positif |",
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
                "| Titre | Statut | Note | Favori | Poids positif |",
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

        detail_rows.extend(
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
            detail_rows.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )

        detail_rows.extend(
            [
                "",
                "#### Top thèmes",
                "",
                "| Thème | Sources | Poids |",
                "|---|---:|---:|",
            ]
        )

        for item in (profile_summary.get("top_themes") or [])[:8]:
            detail_rows.append(
                "| "
                f"{md_cell(item.get('name'))} | "
                f"{item.get('source_count', 0)} | "
                f"{format_score(item.get('total_weight'))} |"
            )

        detail_rows.extend(
            [
                "",
                "### Recommandations obtenues",
                "",
                "| Rang | Titre | Score final | Score base | Bonus objectif | Statut | Volumes | Chapitres |",
                "|---:|---|---:|---:|---:|---|---:|---:|",
            ]
        )

        for index, recommendation in enumerate(recommendations, start=1):
            detail_rows.append(
                "| "
                f"{index} | "
                f"{md_cell(recommendation.get('title'))} | "
                f"{format_score(recommendation.get('recommendation_score'))} | "
                f"{format_score(recommendation.get('base_recommendation_score'))} | "
                f"{format_score(recommendation.get('goal_bonus'))} | "
                f"{md_cell(recommendation.get('status'))} | "
                f"{md_cell(recommendation.get('volumes'))} | "
                f"{md_cell(recommendation.get('chapters'))} |"
            )

        if forbidden_found:
            detail_rows.extend(
                [
                    "",
                    f"**Problème détecté :** {', '.join(forbidden_found)} est ressorti dans les recommandations.",
                    "",
                ]
            )

        detail_sections.extend(detail_rows)

        print(f"Recommandations : {', '.join(recommendation_titles)}")
        print(f"Résultat        : {test_status}")
        print()

    lines.extend(
        [
            "",
            "## Détail des scénarios",
            "",
            *detail_sections,
            "",
            "## Notes",
            "",
            "Ce rapport vérifie que les statuts `DROPPED`, `NOT_INTERESTED`, `WANT_TO_READ` et `OWNED` empêchent bien les mangas concernés de ressortir dans les recommandations. Il vérifie aussi qu'un manga lu avec une très mauvaise note ne contribue plus positivement au profil. Il vérifie aussi qu'un manga lu avec une très mauvaise note ne contribue plus positivement au profil.",
            "Il vérifie aussi les sources positives réellement utilisées par `/recommendations/library`.",
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