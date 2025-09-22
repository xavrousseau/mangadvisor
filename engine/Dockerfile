# ============================================================
# Dockerfile — mangadvisor-engine (service reco)
# Rôle : encapsuler la logique de scoring/re-ranking
# API interne possible (FastAPI minimal) ou gRPC/HTTP léger.
# Ici, on prépare l'environnement Python pour Polars/DuckDB/etc.
# ============================================================

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dépendances système utiles à Polars / DuckDB / build
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python pour un moteur hybride rapide
# (ajuste selon tes besoins exacts)
RUN pip install --no-cache-dir \
      numpy \
      polars \
      duckdb \
      rapidfuzz \
      requests \
      pydantic \
      "psycopg[binary]" \
      redis \
      fastapi uvicorn[standard]

# Copier le code du moteur (ex: server.py si tu exposes une API interne)
COPY . /app

# User non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8080

# Exemple : si tu exposes un micro-serveur FastAPI `server:app`
# Sinon, remplace par un script "python -m engine.job" si c’est un worker.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
