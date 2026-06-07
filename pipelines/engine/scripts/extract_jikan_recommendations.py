"""
Script : extract_jikan_recommendations.py

Rôle :
    Extraire les recommandations communautaires Jikan pour les mangas déjà présents
    dans la table canonique manga.

Entrée :
    PostgreSQL table manga

Sortie :
    data/raw/jikan/recommendations/manga_<mal_id>_recommendations.json

Exemple :
    python pipelines/engine/scripts/extract_jikan_recommendations.py --limit-items 50
    python pipelines/engine/scripts/extract_jikan_recommendations.py --limit-items 250 --force
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from load.postgres_loader import get_postgres_connection  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_RECOMMENDATIONS_DIR = PROJECT_ROOT / "data" / "raw" / "jikan" / "recommendations"

JIKAN_BASE_URL = "https://api.jikan.moe/v4"


def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def fetch_jikan_with_retry(
    url: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay_seconds: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)

            if response.status_code == 429:
                wait_seconds = retry_delay_seconds * attempt
                print(
                    f"[jikan] rate limit 429. "
                    f"Attente {wait_seconds}s avant retry..."
                )
                time.sleep(wait_seconds)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            last_error = exc
            print(f"[jikan] tentative {attempt}/{max_retries} échouée : {exc}")

            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)

    assert last_error is not None
    raise last_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extraire les recommandations communautaires Jikan."
    )

    parser.add_argument(
        "--limit-items",
        type=int,
        default=50,
        help="Nombre maximum de mangas à enrichir.",
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Décalage dans la liste des mangas.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Pause entre deux appels API.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout HTTP en secondes.",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Nombre maximal de tentatives.",
    )

    parser.add_argument(
        "--retry-delay-seconds",
        type=int,
        default=3,
        help="Délai de base entre deux tentatives.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Réextraire même si le fichier JSON existe déjà.",
    )

    return parser.parse_args()


def get_mangas_to_enrich(limit_items: int, offset: int) -> list[dict[str, Any]]:
    """
    Récupère les mangas à enrichir depuis PostgreSQL.

    On privilégie les mangas populaires, car ils ont plus de chances d'avoir
    des recommandations communautaires.
    """
    sql = """
        SELECT
            id,
            source_mal_id,
            title,
            popularity,
            score
        FROM manga
        WHERE source_mal_id IS NOT NULL
        ORDER BY
            popularity ASC NULLS LAST,
            score DESC NULLS LAST,
            title ASC
        LIMIT %s
        OFFSET %s;
    """

    conn = get_postgres_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (limit_items, offset))
            rows = cursor.fetchall()
    finally:
        conn.close()

    mangas: list[dict[str, Any]] = []

    for row in rows:
        # Selon la configuration psycopg, row peut être un dict ou un tuple.
        # On gère les deux cas pour rendre le script robuste.
        if isinstance(row, dict):
            mangas.append(
                {
                    "id": row["id"],
                    "source_mal_id": row["source_mal_id"],
                    "title": row["title"],
                    "popularity": row["popularity"],
                    "score": row["score"],
                }
            )
        else:
            mangas.append(
                {
                    "id": row[0],
                    "source_mal_id": row[1],
                    "title": row[2],
                    "popularity": row[3],
                    "score": row[4],
                }
            )

    return mangas

def output_path_for_manga(mal_id: int) -> Path:
    return RAW_RECOMMENDATIONS_DIR / f"manga_{mal_id}_recommendations.json"


def extract_recommendations_for_manga(
    manga: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[bool, int]:
    mal_id = int(manga["source_mal_id"])
    title = manga["title"]
    output_file = output_path_for_manga(mal_id)

    if output_file.exists() and not args.force:
        print(f"[recommendations] fichier déjà présent, ignoré : {output_file}")

        with output_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        return False, len(payload.get("data", []))

    url = f"{JIKAN_BASE_URL}/manga/{mal_id}/recommendations"

    print(f"[recommendations] extraction : {title} (MAL {mal_id})")
    print(f"[recommendations] url : {url}")

    payload = fetch_jikan_with_retry(
        url=url,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay_seconds=args.retry_delay_seconds,
    )

    save_json(payload, output_file)

    nb_recommendations = len(payload.get("data", []))

    print(f"[recommendations] fichier sauvegardé : {output_file}")
    print(f"[recommendations] recommandations récupérées : {nb_recommendations}")
    print()

    return True, nb_recommendations


def main() -> int:
    args = parse_args()

    if args.limit_items < 1:
        raise ValueError("limit-items doit être >= 1")

    if args.offset < 0:
        raise ValueError("offset doit être >= 0")

    RAW_RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Mangadvisor - Extraction recommandations Jikan")
    print("==================================================")
    print(f"Projet          : {PROJECT_ROOT}")
    print(f"Dossier sortie  : {RAW_RECOMMENDATIONS_DIR}")
    print(f"Limit items     : {args.limit_items}")
    print(f"Offset          : {args.offset}")
    print(f"Sleep seconds   : {args.sleep_seconds}")
    print(f"Force           : {'oui' if args.force else 'non'}")
    print()

    mangas = get_mangas_to_enrich(
        limit_items=args.limit_items,
        offset=args.offset,
    )

    if not mangas:
        print("Aucun manga trouvé à enrichir.")
        return 0

    print(f"Mangas à enrichir : {len(mangas)}")
    print()

    total_api_calls = 0
    total_skipped = 0
    total_recommendations = 0
    total_errors = 0

    for index, manga in enumerate(mangas, start=1):
        print("--------------------------------------------------")
        print(f"{index}/{len(mangas)} - {manga['title']}")
        print("--------------------------------------------------")

        try:
            called_api, nb_recommendations = extract_recommendations_for_manga(
                manga=manga,
                args=args,
            )

            if called_api:
                total_api_calls += 1
            else:
                total_skipped += 1

            total_recommendations += nb_recommendations

        except Exception as exc:
            total_errors += 1
            print(
                f"[recommendations] ERREUR pour {manga['title']} "
                f"(MAL {manga['source_mal_id']}) : {exc}"
            )
            print()

        if index < len(mangas):
            time.sleep(args.sleep_seconds)

    print("==================================================")
    print("Extraction recommandations terminée")
    print(f"Mangas traités                : {len(mangas)}")
    print(f"Appels API effectués          : {total_api_calls}")
    print(f"Fichiers ignorés déjà présents: {total_skipped}")
    print(f"Recommandations récupérées    : {total_recommendations}")
    print(f"Erreurs                       : {total_errors}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())