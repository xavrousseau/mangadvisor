"""
Script : load_jikan_to_postgres.py

Rôle :
    Lire les fichiers JSON bruts extraits depuis Jikan
    et charger les mangas dans PostgreSQL.

Compatibilité V0.6 :
    Par défaut, lit encore :
    data/raw/jikan/manga_page_*.json

V0.7 :
    Peut aussi lire :
    data/raw/jikan/search/search_page_*.json
    data/raw/jikan/top/top_manga_page_*.json

Exemples :
    python pipelines/engine/scripts/load_jikan_to_postgres.py

    python pipelines/engine/scripts/load_jikan_to_postgres.py --sources legacy

    python pipelines/engine/scripts/load_jikan_to_postgres.py --sources search top

    python pipelines/engine/scripts/load_jikan_to_postgres.py --sources all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from load.postgres_loader import get_postgres_connection, upsert_jikan_manga_batch  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_JIKAN_DIR = PROJECT_ROOT / "data" / "raw" / "jikan"


SOURCE_ORDER = ["legacy", "search", "top"]


def parse_published_date(value: Any) -> str | None:
    """
    Convertit une date ISO Jikan en chaîne compatible PostgreSQL.
    """
    if value is None:
        return None

    if isinstance(value, str) and value.strip():
        return value

    return None


def transform_jikan_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """
    Transforme un manga Jikan brut en ligne prête à charger.
    Retourne None si l'enregistrement est invalide.
    """
    mal_id = item.get("mal_id")

    if mal_id is None:
        return None

    published = item.get("published") or {}

    return {
        "mal_id": mal_id,
        "title": item.get("title"),
        "title_english": item.get("title_english"),
        "title_japanese": item.get("title_japanese"),
        "synopsis": item.get("synopsis"),
        "status": item.get("status"),
        "chapters": item.get("chapters"),
        "volumes": item.get("volumes"),
        "score": item.get("score"),
        "popularity": item.get("popularity"),
        "rank": item.get("rank"),
        "members": item.get("members"),
        "favorites": item.get("favorites"),
        "published_from": parse_published_date(published.get("from")),
        "published_to": parse_published_date(published.get("to")),
        "manga_type": item.get("type"),
        "genres_json": json.dumps(item.get("genres", []), ensure_ascii=False),
        "themes_json": json.dumps(item.get("themes", []), ensure_ascii=False),
        "demographics_json": json.dumps(item.get("demographics", []), ensure_ascii=False),
        "authors_json": json.dumps(item.get("authors", []), ensure_ascii=False),
        "serializations_json": json.dumps(
            item.get("serializations", []),
            ensure_ascii=False,
        ),
        "raw_json": json.dumps(item, ensure_ascii=False),
    }


def parse_args() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(
        description="Charger les fichiers JSON Jikan dans PostgreSQL."
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["legacy", "search", "top", "all"],
        default=["legacy"],
        help=(
            "Sources raw à charger. "
            "legacy=data/raw/jikan/manga_page_*.json, "
            "search=data/raw/jikan/search/search_page_*.json, "
            "top=data/raw/jikan/top/top_manga_page_*.json, "
            "all=legacy+search+top."
        ),
    )

    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Désactive la déduplication par mal_id avant chargement.",
    )

    return parser.parse_args()


def normalize_sources(raw_sources: list[str]) -> list[str]:
    """
    Normalise les sources demandées.
    """
    if "all" in raw_sources:
        return SOURCE_ORDER.copy()

    normalized = []

    for source in SOURCE_ORDER:
        if source in raw_sources:
            normalized.append(source)

    return normalized


def iter_jikan_json_files(raw_dir: Path, sources: list[str]) -> list[Path]:
    """
    Retourne la liste triée des fichiers JSON Jikan selon les sources demandées.
    """
    files: list[Path] = []

    if "legacy" in sources:
        files.extend(sorted(raw_dir.glob("manga_page_*.json")))

    if "search" in sources:
        files.extend(sorted((raw_dir / "search").glob("search_page_*.json")))

    if "top" in sources:
        files.extend(sorted((raw_dir / "top").glob("top_manga_page_*.json")))

    return files


def source_label_for_file(file_path: Path) -> str:
    """
    Déduit un libellé de source à partir du chemin du fichier.
    """
    path_as_text = str(file_path).replace("\\", "/")

    if "/search/" in path_as_text:
        return "search"

    if "/top/" in path_as_text:
        return "top"

    return "legacy"


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    Charge un fichier JSON.
    """
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def collect_rows_from_files(
    files: list[Path],
    dedupe: bool = True,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """
    Lit les fichiers JSON, transforme les items, et déduplique par mal_id si demandé.

    Retourne :
    - rows
    - total_items_read
    - total_rows_invalid
    - total_files_in_error
    """
    rows: list[dict[str, Any]] = []
    rows_by_mal_id: dict[int, dict[str, Any]] = {}

    total_items_read = 0
    total_rows_invalid = 0
    total_files_in_error = 0

    for file_path in files:
        source_label = source_label_for_file(file_path)
        print(f"[load_jikan] lecture : {file_path} ({source_label})")

        try:
            payload = load_json_file(file_path)
        except Exception as exc:
            total_files_in_error += 1
            print(f"[load_jikan] ERREUR lecture fichier {file_path.name}: {exc}")
            print()
            continue

        items = payload.get("data", [])

        if not isinstance(items, list):
            total_files_in_error += 1
            print(
                f"[load_jikan] ERREUR format fichier {file_path.name}: "
                "la clé data n'est pas une liste."
            )
            print()
            continue

        valid_in_file = 0
        invalid_in_file = 0

        for item in items:
            if not isinstance(item, dict):
                invalid_in_file += 1
                continue

            total_items_read += 1

            transformed = transform_jikan_item(item)

            if transformed is None:
                invalid_in_file += 1
                continue

            valid_in_file += 1

            if dedupe:
                rows_by_mal_id[int(transformed["mal_id"])] = transformed
            else:
                rows.append(transformed)

        total_rows_invalid += invalid_in_file

        print(f"[load_jikan] items lus : {len(items)}")
        print(f"[load_jikan] lignes valides : {valid_in_file}")
        print(f"[load_jikan] lignes invalides : {invalid_in_file}")
        print()

    if dedupe:
        rows = list(rows_by_mal_id.values())

    rows.sort(key=lambda row: int(row["mal_id"]))

    return rows, total_items_read, total_rows_invalid, total_files_in_error


def main() -> int:
    """
    Point d'entrée principal.
    """
    args = parse_args()
    sources = normalize_sources(args.sources)
    dedupe = not args.no_dedupe

    print("==================================================")
    print("Mangadvisor - Chargement Jikan vers PostgreSQL")
    print("==================================================")
    print(f"Projet              : {PROJECT_ROOT}")
    print(f"Dossier source      : {RAW_JIKAN_DIR}")
    print(f"Sources demandées   : {', '.join(sources)}")
    print(f"Déduplication mal_id: {'oui' if dedupe else 'non'}")
    print()

    files = iter_jikan_json_files(RAW_JIKAN_DIR, sources)

    if not files:
        print("Aucun fichier JSON trouvé pour les sources demandées.")
        print("Lance d'abord l'extraction Jikan.")
        return 0

    print(f"Fichiers détectés : {len(files)}")
    print()

    (
        rows,
        total_items_read,
        total_rows_invalid,
        total_files_in_error,
    ) = collect_rows_from_files(files=files, dedupe=dedupe)

    print("--------------------------------------------------")
    print("Synthèse avant chargement PostgreSQL")
    print("--------------------------------------------------")
    print(f"Total items lus              : {total_items_read}")
    print(f"Total lignes invalides       : {total_rows_invalid}")
    print(f"Total fichiers en erreur     : {total_files_in_error}")
    print(f"Total lignes à charger       : {len(rows)}")
    print()

    if not rows:
        print("Aucune ligne valide à charger.")
        return 0

    conn = get_postgres_connection()

    try:
        loaded = upsert_jikan_manga_batch(conn, rows)
    finally:
        conn.close()

    print("==================================================")
    print("Chargement terminé")
    print(f"Fichiers traités            : {len(files)}")
    print(f"Fichiers en erreur          : {total_files_in_error}")
    print(f"Total items lus             : {total_items_read}")
    print(f"Total lignes valides chargées: {loaded}")
    print(f"Total lignes invalides      : {total_rows_invalid}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())