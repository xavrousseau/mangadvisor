"""
Module Jikan client.

Rôle :
    Fournir des fonctions simples pour appeler l'API Jikan
    et récupérer des pages de mangas.

API utilisée :
    https://api.jikan.moe/v4/manga
"""

from __future__ import annotations

import time
from typing import Any

import requests


JIKAN_BASE_URL = "https://api.jikan.moe/v4/manga"


def fetch_manga_page(page: int = 1, limit: int = 25, timeout: int = 30) -> dict[str, Any]:
    """
    Récupère une page de mangas depuis l'API Jikan.

    Paramètres
    ----------
    page : int
        Numéro de page à récupérer.
    limit : int
        Nombre d'éléments par page.
    timeout : int
        Timeout HTTP en secondes.

    Retour
    ------
    dict
        Réponse JSON complète de l'API Jikan.

    Exceptions
    ----------
    requests.HTTPError
        Si l'API renvoie une erreur HTTP.
    requests.RequestException
        Si un problème réseau survient.
    """
    params = {
        "page": page,
        "limit": limit,
    }

    response = requests.get(JIKAN_BASE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_manga_page_with_retry(
    page: int = 1,
    limit: int = 25,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay_seconds: int = 3,
) -> dict[str, Any]:
    """
    Récupère une page Jikan avec une logique simple de retry.

    Paramètres
    ----------
    page : int
        Numéro de page.
    limit : int
        Nombre d'éléments par page.
    timeout : int
        Timeout HTTP en secondes.
    max_retries : int
        Nombre maximal de tentatives.
    retry_delay_seconds : int
        Temps d'attente entre deux tentatives.

    Retour
    ------
    dict
        Réponse JSON de l'API.

    Exceptions
    ----------
    requests.RequestException
        Si toutes les tentatives échouent.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return fetch_manga_page(page=page, limit=limit, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            print(
                f"[jikan_client] tentative {attempt}/{max_retries} échouée "
                f"pour la page {page}: {exc}"
            )
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)

    assert last_error is not None
    raise last_error