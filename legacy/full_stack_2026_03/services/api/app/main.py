# =============================================================================
# Mangadvisor API — FastAPI + métriques Prometheus + health/readiness
# Étape 1 : endpoints minimaux, métriques légères, aucun index ANN côté DB.
# =============================================================================

from __future__ import annotations

import os
import json
import logging
from time import perf_counter
from typing import Callable

import httpx
import psycopg
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app


# -----------------------------------------------------------------------------
# App FastAPI (titre/version affichés dans /docs)
# -----------------------------------------------------------------------------
app = FastAPI(title="Mangadvisor API", version="0.1.0")


# -----------------------------------------------------------------------------
# Logs "ATS-like" très simples (JSON par ligne, sans dépendance externe)
# -----------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "logger": record.name,
        }
        # Ajoute des infos additionnelles si présentes
        if hasattr(record, "path"):
            payload["path"] = getattr(record, "path")
        if hasattr(record, "method"):
            payload["method"] = getattr(record, "method")
        if hasattr(record, "status"):
            payload["status"] = getattr(record, "status")
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = getattr(record, "duration_ms")
        return json.dumps(payload, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("mangadvisor.api")


# -----------------------------------------------------------------------------
# Métriques Prometheus (noms stables et lisibles)
# -----------------------------------------------------------------------------
REQ_TOTAL = Counter(
    "mangadvisor_requests_total",
    "Nombre de requêtes API",
    ["endpoint", "method"],
)
ERR_TOTAL = Counter(
    "mangadvisor_errors_total",
    "Erreurs par endpoint/méthode/code",
    ["endpoint", "method", "status"],
)
REQ_LATENCY = Histogram(
    "mangadvisor_request_latency_seconds",
    "Latence des endpoints (s)",
    ["endpoint", "method"],
    buckets=[0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2, 3, 5],
)

# Endpoints à exclure des métriques pour éviter le bruit
NO_METRICS_PATHS = {"/metrics", "/health", "/healthz", "/readyz", "/docs", "/openapi.json"}


# -----------------------------------------------------------------------------
# Middleware de métriques (+ logs)
# -----------------------------------------------------------------------------
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        start = perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # On registre l'erreur avant de relancer l'exception
            status_code = 500
            raise
        finally:
            duration = perf_counter() - start

            # Log JSON concis
            log_extra = {
                "path": path,
                "method": method,
                "status": status_code,
                "duration_ms": round(duration * 1000, 2),
            }
            log.info("request", extra=log_extra)

            # Métriques (on ignore les endpoints bruités)
            if path not in NO_METRICS_PATHS:
                REQ_TOTAL.labels(endpoint=path, method=method).inc()
                REQ_LATENCY.labels(endpoint=path, method=method).observe(duration)
                if status_code >= 400:
                    ERR_TOTAL.labels(endpoint=path, method=method, status=str(status_code)).inc()


app.add_middleware(MetricsMiddleware)


# -----------------------------------------------------------------------------
# Health / Readiness
# - /health     : liveness rapide (OK si l'app répond)
# - /healthz    : alias pour le compose/HC (même comportement que /health)
# - /readyz     : readiness (DB + Ollama), timeouts courts
# -----------------------------------------------------------------------------
@app.get("/health", include_in_schema=False)
def health() -> dict:
    """Liveness simple : si l'app répond, c'est OK."""
    return {"ok": True}


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    """Alias utilisé par le healthcheck Docker."""
    return {"ok": True}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> dict:
    """Vérifie la DB et l'API d'Ollama (readiness)."""
    dsn = os.getenv("DATABASE_URL")
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://mangadvisor-ollama:11434")

    ok_db = False
    ok_ollama = False

    # DB : connexion courte + SELECT 1
    try:
        if not dsn:
            raise RuntimeError("DATABASE_URL manquant")
        with psycopg.connect(dsn, connect_timeout=2) as conn:
            conn.execute("select 1;")
        ok_db = True
    except Exception as e:
        log.warning(f"readyz-db-error: {e}")

    # Ollama : GET /api/tags (timeout court)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{ollama_base}/api/tags")
            r.raise_for_status()
        ok_ollama = True
    except Exception as e:
        log.warning(f"readyz-ollama-error: {e}")

    status = "ok" if (ok_db and ok_ollama) else "degraded"
    return {"status": status, "db": ok_db, "ollama": ok_ollama}


# -----------------------------------------------------------------------------
# Exemple d'endpoint applicatif (placeholder)
# -----------------------------------------------------------------------------
@app.get("/recommend")
def recommend(limit: int = 5) -> dict:
    """
    Démo : renvoie une liste vide avec un paramètre limit.
    Remplace par ta logique réelle de recommandation / similarité.
    """
    return {"items": [], "limit": limit}


# -----------------------------------------------------------------------------
# Exposer /metrics pour Prometheus (texte en plain/text)
# -----------------------------------------------------------------------------
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
