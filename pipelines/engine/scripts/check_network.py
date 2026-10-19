"""Read-only diagnostic for the configured MAL-compatible manga API.

The public api.jikan.moe service closed on 1 October 2026. Mangadvisor
uses Tenrai v1 by default and validates real JSON over HTTPS before ingestion.
"""
from __future__ import annotations

import errno
import os
import socket
import ssl
from urllib.parse import urlparse

import requests

DEFAULT_API_BASE = "https://api.tenrai.org/v1"


def api_base() -> str:
    base = os.getenv("MANGA_API_BASE_URL", DEFAULT_API_BASE).strip().rstrip("/")
    url = urlparse(base)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("MANGA_API_BASE_URL doit etre une URL HTTPS valide, sans identifiants ni parametres.")
    if url.hostname == "api.jikan.moe":
        raise ValueError("api.jikan.moe est arrete depuis le 1er octobre 2026 : utiliser Tenrai v1.")
    return base


def check_https(host: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return False, f"DNS non fonctionnel pour {host}: {exc}"
    try:
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
                return True, f"HTTPS accessible: {host} ({tls.version()})"
    except OSError as exc:
        if getattr(exc, "errno", None) in (errno.ENETUNREACH, errno.EHOSTUNREACH):
            return False, f"Reseau injoignable depuis Docker pour {host}: {exc}"
        if isinstance(exc, (socket.timeout, TimeoutError)):
            return False, f"Connexion expiree vers {host}: {exc}"
        if isinstance(exc, ssl.SSLError):
            return False, f"Probleme TLS / proxy vers {host}: {exc}"
        return False, f"Connexion impossible vers {host}: {exc}"


def check_provider(base: str) -> tuple[bool, str]:
    """Validate a real manga response, not just a successful TLS handshake."""
    url = f"{base}/manga"
    try:
        response = requests.get(url, params={"page": 1, "limit": 1}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            return False, "API manga : JSON non compatible (data doit contenir des notices)."
        if not isinstance(items[0].get("mal_id"), int) or not items[0].get("title"):
            return False, "API manga : notice sans mal_id/titre, import bloque."
    except (requests.RequestException, ValueError) as exc:
        return False, f"API manga inaccessible : {exc}"
    return True, f"API manga valide : {url} (une notice MAL avec ID et titre)."


def main() -> int:
    print("=== Diagnostic de la source manga depuis le conteneur Docker ===", flush=True)
    try:
        base = api_base()
    except ValueError as exc:
        print(f"ERREUR configuration : {exc}", flush=True)
        return 2
    host = urlparse(base).hostname
    print(f"Fournisseur configure : {base}", flush=True)
    external_ok, external_msg = check_https("example.com")
    provider_ok, provider_msg = check_https(host)
    print(external_msg, flush=True)
    print(provider_msg, flush=True)
    if provider_ok:
        valid, check_msg = check_provider(base)
        print(check_msg, flush=True)
        if valid:
            print("OK : une reponse API manga exploitable a ete recue.", flush=True)
            return 0
    print("", flush=True)
    if not external_ok and not provider_ok:
        print("HTTPS sortant inaccessible dans Docker : verifier Desktop, VPN, proxy et pare-feu.", flush=True)
    elif not provider_ok:
        print("L'hote du fournisseur est inaccessible depuis Docker.", flush=True)
    else:
        print("La connexion HTTPS fonctionne, mais l'API ne renvoie pas de catalogue valide.", flush=True)
    print(f"1. Ouvrir {base}/manga?page=1&limit=1 dans le navigateur Windows.", flush=True)
    print("2. Dans Docker Desktop : Troubleshoot > Restart Docker Desktop.", flush=True)
    print("3. Si besoin : verifier Settings > Resources > Proxies, VPN et pare-feu.", flush=True)
    print("4. Relancer l'option 29, puis le catalogue (option 25).", flush=True)
    print("Ne pas lancer Nuke : aucune suppression SQL necessaire.", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
