"""
Script : run_jikan_pipeline.py

Rôle :
    Orchestrer le pipeline Jikan de bout en bout :
    1. nettoyage optionnel de la table PostgreSQL
    2. extraction depuis l'API Jikan
    3. chargement des JSON dans PostgreSQL

Exemples :
    python pipelines/engine/scripts/run_jikan_pipeline.py
    python pipelines/engine/scripts/run_jikan_pipeline.py --start-page 1 --end-page 3 --limit 10
    python pipelines/engine/scripts/run_jikan_pipeline.py --reset-db --start-page 1 --end-page 3
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = PROJECT_ROOT / "pipelines" / "engine" / "scripts"

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from load.postgres_loader import get_postgres_connection  # noqa: E402


def parse_args() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(
        description="Lancer le pipeline Jikan complet : reset optionnel + extraction + chargement."
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Première page Jikan à extraire.",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=1,
        help="Dernière page Jikan à extraire.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de mangas par page.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Vide la table jikan_manga_source avant le chargement.",
    )
    return parser.parse_args()


def run_python_script(script_path: Path, args: list[str]) -> None:
    """
    Exécute un script Python avec les arguments fournis.

    Paramètres
    ----------
    script_path : Path
        Chemin vers le script Python.
    args : list[str]
        Arguments à transmettre.
    """
    command = [sys.executable, str(script_path), *args]

    print("--------------------------------------------------")
    print(f"Exécution : {' '.join(command)}")
    print("--------------------------------------------------")

    result = subprocess.run(command, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        raise RuntimeError(
            f"Le script {script_path.name} a échoué avec le code {result.returncode}."
        )


def reset_jikan_source_table() -> None:
    """
    Vide complètement la table source Jikan.
    """
    print("--------------------------------------------------")
    print("Nettoyage PostgreSQL : jikan_manga_source")
    print("--------------------------------------------------")

    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE jikan_manga_source RESTART IDENTITY;")
        conn.commit()
        print("[run_jikan_pipeline] table jikan_manga_source vidée avec succès.")
    finally:
        conn.close()


def main() -> None:
    """
    Point d'entrée principal.
    """
    args = parse_args()

    if args.start_page < 1:
        raise ValueError("start-page doit être >= 1")
    if args.end_page < args.start_page:
        raise ValueError("end-page doit être >= start-page")
    if args.limit < 1:
        raise ValueError("limit doit être >= 1")

    extract_script = SCRIPTS_DIR / "extract_jikan.py"
    load_script = SCRIPTS_DIR / "load_jikan_to_postgres.py"

    print("==================================================")
    print("Mangadvisor - Pipeline Jikan complet")
    print("==================================================")
    print(f"Projet : {PROJECT_ROOT}")
    print(f"Pages : {args.start_page} à {args.end_page}")
    print(f"Limit : {args.limit}")
    print(f"Reset DB : {'oui' if args.reset_db else 'non'}")
    print()

    if args.reset_db:
        reset_jikan_source_table()
        print()

    extract_args = [
        "--start-page",
        str(args.start_page),
        "--end-page",
        str(args.end_page),
        "--limit",
        str(args.limit),
    ]

    run_python_script(extract_script, extract_args)
    print()
    run_python_script(load_script, [])
    print()

    print("==================================================")
    print("Pipeline Jikan terminé avec succès")
    print("==================================================")


if __name__ == "__main__":
    main()