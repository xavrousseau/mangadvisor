# FastAPI + métriques Prometheus pour mangadvisor-api
from time import perf_counter
from typing import Callable
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI(title="Mangadvisor API")

# --- Métriques (noms simples et stables) ---
REQ_TOTAL = Counter(
    "mangadvisor_requests_total",
    "Nombre de requêtes API",
    ["endpoint", "method"]
)
ERR_TOTAL = Counter(
    "mangadvisor_errors_total",
    "Erreurs par endpoint/méthode/code",
    ["endpoint", "method", "status"]
)
REQ_LATENCY = Histogram(
    "mangadvisor_request_latency_seconds",
    "Latence des endpoints (s)",
    ["endpoint", "method"],
    # Buckets raisonnables pour API web
    buckets=[0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 1.5, 2, 3, 5]
)

# --- Middleware de métriques ---
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        # Option : regrouper les chemins dynamiques si besoin (ex: /item/123 -> /item/:id)
        endpoint = path
        method = request.method

        start = perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            duration = perf_counter() - start
            REQ_TOTAL.labels(endpoint=endpoint, method=method).inc()
            REQ_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

app.add_middleware(MetricsMiddleware)

# --- Endpoints de ton appli ---
@app.get("/health")
def health():
    return {"ok": True}

# (exemple)
@app.get("/recommend")
def recommend(limit: int = 5):
    # ... ta logique ...
    return {"items": [], "limit": limit}

# --- Exposer /metrics ---
# make_asgi_app() crée une app ASGI qui expose les métriques en texte Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
