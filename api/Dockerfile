# ============================================================
# Dockerfile — mangadvisor-api (FastAPI)
# Rôle : expose /recommend, /feedback, /health (+ /metrics si tu veux)
# Base légère + user non-root + cache pip
# ============================================================

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---- Dépendances système minimales (certifs, curl pour health, build léger) ----
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Dépendances Python (séparées pour profiter du cache Docker) ----
# Si tu préfères un requirements.txt, remplace le bloc RUN pip install par COPY requirements.txt + pip install -r requirements.txt
RUN pip install --no-cache-dir \
      fastapi \
      uvicorn[standard] \
      pydantic \
      numpy \
      requests \
      redis \
      "psycopg[binary]" \
      prometheus-client

# ---- Copier le code de l'API ----
# Arborescence attendue : /app/main.py, /app/storage.py, /app/reco.py, etc.
COPY ./app /app

# ---- User non-root pour sécurité ----
RUN useradd -m appuser
USER appuser

# ---- Exposer le port interne de l'API ----
EXPOSE 8000

# ---- Commande de démarrage (Uvicorn) ----
# Remplace "main:app" si ton module FastAPI a un chemin différent.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
