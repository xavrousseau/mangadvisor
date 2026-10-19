"""Read-only connectivity diagnostic inside the *same* Docker engine network as Jikan.

No API token, DB credential, mutation, or manga download is involved.
A TCP+TLS handshake verifies the outbound route before long Jikan extractions.
"""
from __future__ import annotations

import errno
import socket
import ssl


def check_https(host: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        # Test DNS explicitly before connecting, to distinguish resolver vs routing errors.
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return False, f"DNS non fonctionnel pour {host}: {exc}"

    try:
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as tls:
                if tls.version():
                    return True, f"HTTPS accessible: {host} ({tls.version()})"
                return True, f"HTTPS accessible: {host}"
    except OSError as exc:
        if getattr(exc, "errno", None) in (errno.ENETUNREACH, errno.EHOSTUNREACH):
            return False, f"Reseau injoignable depuis Docker pour {host}: {exc}"
        if isinstance(exc, (socket.timeout, TimeoutError)):
            return False, f"Connexion expiree vers {host}: {exc}"
        if isinstance(exc, ssl.SSLError):
            return False, f"Probleme TLS / proxy vers {host}: {exc}"
        return False, f"Connexion impossible vers {host}: {exc}"


def main() -> int:
    print("=== Diagnostic HTTPS depuis le conteneur engine de Mangadvisor ===", flush=True)
    external_ok, external_msg = check_https("example.com")
    jikan_ok, jikan_msg = check_https("api.jikan.moe")
    print(external_msg, flush=True)
    print(jikan_msg, flush=True)
    if jikan_ok:
        print("OK : le conteneur peut joindre l'API Jikan en HTTPS.", flush=True)
        return 0
    print("", flush=True)
    if not external_ok:
        print("Aucun acces HTTPS sortant confirme : verifier Docker Desktop, VPN, proxy et pare-feu.", flush=True)
    else:
        print("Internet fonctionne dans Docker, mais api.jikan.moe est inaccessible.", flush=True)
        print("Verifier un filtrage du domaine, le proxy ou une indisponibilite temporaire.", flush=True)
    print("1. Ouvrir https://api.jikan.moe/v4/manga?page=1&limit=1 dans le navigateur Windows.", flush=True)
    print("2. Dans Docker Desktop : Troubleshoot > Restart Docker Desktop.", flush=True)
    print("3. Si besoin : verifier Settings > Resources > Proxies, VPN et pare-feu.", flush=True)
    print("4. Relancer le diagnostic (option 29), puis le catalogue (option 25).", flush=True)
    print("Ne pas lancer Nuke : le catalogue SQL et les volumes ne sont pas en cause.", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
