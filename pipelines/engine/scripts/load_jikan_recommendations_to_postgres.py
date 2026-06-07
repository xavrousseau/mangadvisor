"""
Script : load_jikan_recommendations_to_postgres.py

Rôle :
    Charger en base PostgreSQL les recommandations communautaires Jikan
    extraites dans data/raw/jikan/recommendations.

Entrée :
    data/raw/jikan/recommendations/manga_<mal_id>_recommendations.json

Sortie :
    table manga_recommendation_edge

Exemple :
    python pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py
    python pipelines/engine/scripts/load_jikan_recommendations_to_postgres.py --reset
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from load.postgres_loader import get_postgres_connection  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_RECOMMENDATIONS_DIR = PROJECT_ROOT / "data" / "raw" / "jikan" / "recommendations"


FILENAME_PATTERN = re.compile(r"manga_(\d+)_recommendations\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Charger les recommandations communautaires Jikan dans PostgreSQL."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Vide la table manga_recommendation_edge avant chargement.",
    )

    return parser.parse_args()


def extract_source_mal_id(file_path: Path) -> int | None:
    """
    Extrait le MAL ID source depuis le nom du fichier.
    Exemple : manga_11_recommendations.json -> 11
    """
    match = FILENAME_PATTERN.match(file_path.name)

    if not match:
        return None

    return int(match.group(1))


def load_json_file(file_path: Path) -> dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_manga_mapping(conn) -> tuple[dict[int, int], dict[int, str]]:
    """
    Retourne deux mappings :
    - source_mal_id -> manga.id
    - source_mal_id -> manga.title
    """
    sql = """
        SELECT
            id,
            source_mal_id,
            title
        FROM manga
        WHERE source_mal_id IS NOT NULL;
    """

    mapping_id: dict[int, int] = {}
    mapping_title: dict[int, str] = {}

    with conn.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    for row in rows:
        if isinstance(row, dict):
            mal_id = row["source_mal_id"]
            manga_id = row["id"]
            title = row["title"]
        else:
            manga_id = row[0]
            mal_id = row[1]
            title = row[2]

        if mal_id is None:
            continue

        mapping_id[int(mal_id)] = int(manga_id)
        mapping_title[int(mal_id)] = title

    return mapping_id, mapping_title


def parse_recommendation_item(
    source_manga_id: int,
    item: dict[str, Any],
    mal_id_to_manga_id: dict[int, int],
) -> dict[str, Any] | None:
    """
    Transforme un item Jikan recommendation en ligne PostgreSQL.

    Format attendu Jikan :
    {
      "entry": {
        "mal_id": ...,
        "title": ...
      },
      "votes": ...
    }
    """
    entry = item.get("entry") or {}

    recommended_mal_id = entry.get("mal_id")

    if recommended_mal_id is None:
        return None

    recommended_mal_id = int(recommended_mal_id)

    return {
        "source_manga_id": source_manga_id,
        "recommended_mal_id": recommended_mal_id,
        "recommended_manga_id": mal_id_to_manga_id.get(recommended_mal_id),
        "recommended_title": entry.get("title"),
        "votes": item.get("votes"),
        "raw_json": json.dumps(item, ensure_ascii=False),
    }


def iter_recommendation_files() -> list[Path]:
    return sorted(RAW_RECOMMENDATIONS_DIR.glob("manga_*_recommendations.json"))


def reset_table(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE manga_recommendation_edge;")

    conn.commit()


def upsert_recommendation_rows(conn, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    sql = """
        INSERT INTO manga_recommendation_edge (
            source_manga_id,
            recommended_mal_id,
            recommended_manga_id,
            recommended_title,
            votes,
            raw_json,
            loaded_at
        )
        VALUES (
            %(source_manga_id)s,
            %(recommended_mal_id)s,
            %(recommended_manga_id)s,
            %(recommended_title)s,
            %(votes)s,
            %(raw_json)s::jsonb,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (source_manga_id, recommended_mal_id)
        DO UPDATE SET
            recommended_manga_id = EXCLUDED.recommended_manga_id,
            recommended_title = EXCLUDED.recommended_title,
            votes = EXCLUDED.votes,
            raw_json = EXCLUDED.raw_json,
            loaded_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)

    conn.commit()

    return len(rows)


def main() -> int:
    args = parse_args()

    print("==================================================")
    print("Mangadvisor - Chargement recommandations Jikan")
    print("==================================================")
    print(f"Projet         : {PROJECT_ROOT}")
    print(f"Dossier source : {RAW_RECOMMENDATIONS_DIR}")
    print(f"Reset table    : {'oui' if args.reset else 'non'}")
    print()

    files = iter_recommendation_files()

    if not files:
        print("Aucun fichier de recommandations trouvé.")
        print("Lance d'abord : cmd\\extract-jikan-recommendations.cmd")
        return 0

    print(f"Fichiers détectés : {len(files)}")
    print()

    conn = get_postgres_connection()

    try:
        if args.reset:
            print("[load_recommendations] nettoyage table manga_recommendation_edge...")
            reset_table(conn)
            print("[load_recommendations] table vidée.")
            print()

        mal_id_to_manga_id, mal_id_to_title = get_manga_mapping(conn)

        print(f"Mangas référencés dans le catalogue : {len(mal_id_to_manga_id)}")
        print()

        all_rows: list[dict[str, Any]] = []

        total_files_in_error = 0
        total_items_read = 0
        total_items_invalid = 0
        total_sources_missing = 0
        total_recommended_linked = 0
        total_recommended_not_in_catalog = 0

        for file_path in files:
            source_mal_id = extract_source_mal_id(file_path)

            if source_mal_id is None:
                print(f"[load_recommendations] fichier ignoré, nom invalide : {file_path.name}")
                continue

            source_manga_id = mal_id_to_manga_id.get(source_mal_id)

            if source_manga_id is None:
                total_sources_missing += 1
                print(
                    f"[load_recommendations] source absente du catalogue, fichier ignoré : "
                    f"{file_path.name}"
                )
                continue

            source_title = mal_id_to_title.get(source_mal_id, f"MAL {source_mal_id}")

            print(f"[load_recommendations] lecture : {file_path.name} - {source_title}")

            try:
                payload = load_json_file(file_path)
            except Exception as exc:
                total_files_in_error += 1
                print(f"[load_recommendations] ERREUR lecture : {exc}")
                print()
                continue

            items = payload.get("data", [])

            if not isinstance(items, list):
                total_files_in_error += 1
                print("[load_recommendations] ERREUR format : data n'est pas une liste.")
                print()
                continue

            valid_in_file = 0
            invalid_in_file = 0
            linked_in_file = 0
            not_linked_in_file = 0

            for item in items:
                if not isinstance(item, dict):
                    invalid_in_file += 1
                    continue

                total_items_read += 1

                row = parse_recommendation_item(
                    source_manga_id=source_manga_id,
                    item=item,
                    mal_id_to_manga_id=mal_id_to_manga_id,
                )

                if row is None:
                    invalid_in_file += 1
                    continue

                valid_in_file += 1

                if row["recommended_manga_id"] is not None:
                    linked_in_file += 1
                else:
                    not_linked_in_file += 1

                all_rows.append(row)

            total_items_invalid += invalid_in_file
            total_recommended_linked += linked_in_file
            total_recommended_not_in_catalog += not_linked_in_file

            print(f"[load_recommendations] items lus          : {len(items)}")
            print(f"[load_recommendations] lignes valides     : {valid_in_file}")
            print(f"[load_recommendations] lignes invalides   : {invalid_in_file}")
            print(f"[load_recommendations] recommandés liés   : {linked_in_file}")
            print(f"[load_recommendations] hors catalogue     : {not_linked_in_file}")
            print()

        loaded = upsert_recommendation_rows(conn, all_rows)

    finally:
        conn.close()

    print("==================================================")
    print("Chargement recommandations terminé")
    print(f"Fichiers traités                    : {len(files)}")
    print(f"Fichiers en erreur                  : {total_files_in_error}")
    print(f"Sources absentes du catalogue       : {total_sources_missing}")
    print(f"Items lus                           : {total_items_read}")
    print(f"Items invalides                     : {total_items_invalid}")
    print(f"Lignes chargées                     : {loaded}")
    print(f"Recommandations liées au catalogue  : {total_recommended_linked}")
    print(f"Recommandations hors catalogue      : {total_recommended_not_in_catalog}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())