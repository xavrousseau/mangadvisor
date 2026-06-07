"""
Script : extract_jikan.py

Rôle :
    Extraire des données manga depuis l'API Jikan
    et enregistrer les réponses JSON brutes dans data/raw/jikan.

Modes disponibles :
    search : extraction depuis /manga
    top    : extraction depuis /top/manga

Sorties V0.7 :
    data/raw/jikan/search/search_page_1.json
    data/raw/jikan/top/top_manga_page_1.json

Compatibilité V0.6 :
    En mode search, le script écrit aussi par défaut une copie legacy :
    data/raw/jikan/manga_page_1.json

    Cela permet de ne pas casser le pipeline actuel :
    cmd\\run-jikan-pipeline.cmd
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_JIKAN_DIR = PROJECT_ROOT / "data" / "raw" / "jikan"

JIKAN_BASE_URL = "https://api.jikan.moe/v4"


def save_json(data: dict[str, Any], output_path: Path) -> None:
    """
    Enregistre un dictionnaire Python en JSON formaté.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def clean_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    Supprime les paramètres non renseignés avant l'appel API.
    """
    cleaned: dict[str, Any] = {}

    for key, value in params.items():
        if value is None:
            continue

        if isinstance(value, str) and value.strip() == "":
            continue

        cleaned[key] = value

    return cleaned


def fetch_jikan_with_retry(
    endpoint: str,
    params: dict[str, Any],
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay_seconds: int = 3,
) -> dict[str, Any]:
    """
    Appelle un endpoint Jikan avec une logique simple de retry.

    Paramètres
    ----------
    endpoint :
        Endpoint Jikan, par exemple "/manga" ou "/top/manga".
    params :
        Paramètres de requête.
    timeout :
        Timeout HTTP en secondes.
    max_retries :
        Nombre maximal de tentatives.
    retry_delay_seconds :
        Délai entre deux tentatives.

    Retour
    ------
    dict
        Réponse JSON complète de l'API Jikan.
    """
    url = f"{JIKAN_BASE_URL}{endpoint}"
    cleaned_params = clean_params(params)

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=cleaned_params, timeout=timeout)

            if response.status_code == 429:
                wait_seconds = retry_delay_seconds * attempt
                print(
                    f"[jikan] rate limit 429 sur {endpoint}. "
                    f"Attente {wait_seconds}s avant retry..."
                )
                time.sleep(wait_seconds)
                response.raise_for_status()

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            last_error = exc
            print(
                f"[jikan] tentative {attempt}/{max_retries} échouée "
                f"pour {endpoint} avec params={cleaned_params}: {exc}"
            )

            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)

    assert last_error is not None
    raise last_error


def build_search_params(args: argparse.Namespace, page: int) -> dict[str, Any]:
    """
    Construit les paramètres pour l'endpoint /manga.
    """
    return clean_params(
        {
            "page": page,
            "limit": args.limit,
            "q": args.query,
            "type": args.manga_type,
            "status": args.status,
            "order_by": args.order_by,
            "sort": args.sort,
            "min_score": args.min_score,
            "max_score": args.max_score,
            "genres": args.genres,
            "genres_exclude": args.genres_exclude,
            "sfw": args.sfw,
            "unapproved": args.unapproved,
        }
    )


def build_top_params(args: argparse.Namespace, page: int) -> dict[str, Any]:
    """
    Construit les paramètres pour l'endpoint /top/manga.
    """
    return clean_params(
        {
            "page": page,
            "limit": args.limit,
            "type": args.manga_type,
            "filter": args.top_filter,
        }
    )


def output_path_for_mode(mode: str, page: int) -> Path:
    """
    Retourne le chemin de sortie principal selon le mode.
    """
    if mode == "search":
        return RAW_JIKAN_DIR / "search" / f"search_page_{page}.json"

    if mode == "top":
        return RAW_JIKAN_DIR / "top" / f"top_manga_page_{page}.json"

    raise ValueError(f"Mode non supporté : {mode}")


def legacy_search_output_path(page: int) -> Path:
    """
    Chemin legacy utilisé par le pipeline V0.6.
    """
    return RAW_JIKAN_DIR / f"manga_page_{page}.json"


def parse_args() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(
        description="Extraire des données manga depuis l'API Jikan."
    )

    parser.add_argument(
        "--mode",
        choices=["search", "top"],
        default="search",
        help="Mode d'extraction : search=/manga, top=/top/manga.",
    )

    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Première page à extraire.",
    )

    parser.add_argument(
        "--end-page",
        type=int,
        default=1,
        help="Dernière page à extraire.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Nombre de mangas par page.",
    )

    parser.add_argument(
        "--query",
        "--q",
        dest="query",
        default=None,
        help="Recherche texte pour le mode search. Exemple : Naruto.",
    )

    parser.add_argument(
        "--manga-type",
        default=None,
        help="Type manga Jikan. Exemples : manga, novel, lightnovel, oneshot, doujin, manhwa, manhua.",
    )

    parser.add_argument(
        "--status",
        default=None,
        help="Statut pour le mode search. Exemples : publishing, complete, hiatus, discontinued, upcoming.",
    )

    parser.add_argument(
        "--order-by",
        default=None,
        help="Tri pour le mode search. Exemples : popularity, score, rank, members, favorites.",
    )

    parser.add_argument(
        "--sort",
        choices=["asc", "desc"],
        default=None,
        help="Sens de tri pour le mode search.",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Score minimum pour le mode search.",
    )

    parser.add_argument(
        "--max-score",
        type=float,
        default=None,
        help="Score maximum pour le mode search.",
    )

    parser.add_argument(
        "--genres",
        default=None,
        help="IDs de genres à inclure, séparés par des virgules. Exemple : 1,2,10.",
    )

    parser.add_argument(
        "--genres-exclude",
        default=None,
        help="IDs de genres à exclure, séparés par des virgules. Exemple : 9,12.",
    )

    parser.add_argument(
        "--sfw",
        choices=["true", "false"],
        default="true",
        help="Filtre SFW pour le mode search.",
    )

    parser.add_argument(
        "--unapproved",
        choices=["true", "false"],
        default=None,
        help="Inclure ou non les entrées non approuvées pour le mode search.",
    )

    parser.add_argument(
        "--top-filter",
        default=None,
        help="Filtre pour le mode top. Exemple : publishing, upcoming, bypopularity, favorite.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Pause entre deux appels API pour respecter les limites Jikan.",
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
        help="Nombre maximal de tentatives en cas d'erreur réseau ou API.",
    )

    parser.add_argument(
        "--retry-delay-seconds",
        type=int,
        default=3,
        help="Délai de base entre deux retries.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Réextraire même si le fichier de sortie existe déjà.",
    )

    parser.add_argument(
        "--no-legacy-search-copy",
        action="store_true",
        help="Désactive la copie legacy data/raw/jikan/manga_page_X.json en mode search.",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """
    Valide les arguments utilisateur.
    """
    if args.start_page < 1:
        raise ValueError("start-page doit être >= 1")

    if args.end_page < args.start_page:
        raise ValueError("end-page doit être >= start-page")

    if args.limit < 1:
        raise ValueError("limit doit être >= 1")

    if args.limit > 25:
        print(
            "[extract_jikan] ATTENTION : Jikan recommande généralement limit <= 25. "
            f"Valeur reçue : {args.limit}"
        )

    if args.mode == "top":
        ignored_for_top = [
            args.query,
            args.status,
            args.order_by,
            args.sort,
            args.min_score,
            args.max_score,
            args.genres,
            args.genres_exclude,
            args.unapproved,
        ]

        if any(value is not None for value in ignored_for_top):
            print(
                "[extract_jikan] INFO : certains paramètres search sont ignorés en mode top "
                "(query, status, order_by, sort, min_score, max_score, genres, genres_exclude, unapproved)."
            )


def extract_page(args: argparse.Namespace, page: int) -> tuple[Path, int]:
    """
    Extrait une page selon le mode choisi et sauvegarde le JSON.
    """
    if args.mode == "search":
        endpoint = "/manga"
        params = build_search_params(args, page)

    elif args.mode == "top":
        endpoint = "/top/manga"
        params = build_top_params(args, page)

    else:
        raise ValueError(f"Mode non supporté : {args.mode}")

    output_file = output_path_for_mode(args.mode, page)

    if output_file.exists() and not args.force:
        print(
            f"[extract_jikan] fichier déjà présent, extraction ignorée : {output_file}"
        )

        with output_file.open("r", encoding="utf-8") as file:
            existing_payload = json.load(file)

        return output_file, len(existing_payload.get("data", []))

    print(f"[extract_jikan] récupération page {page} via {endpoint}...")
    print(f"[extract_jikan] paramètres : {params}")

    payload = fetch_jikan_with_retry(
        endpoint=endpoint,
        params=params,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay_seconds=args.retry_delay_seconds,
    )

    save_json(payload, output_file)

    if args.mode == "search" and not args.no_legacy_search_copy:
        legacy_file = legacy_search_output_path(page)
        save_json(payload, legacy_file)
        print(f"[extract_jikan] copie legacy sauvegardée : {legacy_file}")

    nb_items = len(payload.get("data", []))

    print(f"[extract_jikan] page sauvegardée : {output_file}")
    print(f"[extract_jikan] mangas récupérés : {nb_items}")
    print()

    return output_file, nb_items


def main() -> int:
    """
    Point d'entrée principal du script.
    """
    args = parse_args()
    validate_args(args)

    RAW_JIKAN_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Mangadvisor - Extraction Jikan V0.7")
    print("==================================================")
    print(f"Projet              : {PROJECT_ROOT}")
    print(f"Dossier raw Jikan   : {RAW_JIKAN_DIR}")
    print(f"Mode                : {args.mode}")
    print(f"Pages               : {args.start_page} à {args.end_page}")
    print(f"Limit               : {args.limit}")
    print(f"Sleep seconds       : {args.sleep_seconds}")
    print(f"Force               : {'oui' if args.force else 'non'}")
    print()

    total_pages = 0
    total_items = 0

    for page in range(args.start_page, args.end_page + 1):
        _output_file, nb_items = extract_page(args, page)

        total_pages += 1
        total_items += nb_items

        if page < args.end_page:
            time.sleep(args.sleep_seconds)

    print("==================================================")
    print("Extraction terminée")
    print(f"Mode                   : {args.mode}")
    print(f"Nombre de pages traitées : {total_pages}")
    print(f"Nombre total d'items      : {total_items}")
    print("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())