# ============================================================
# Dockerfile — mangadvisor-api (FastAPI)
# Étape 1 : lean & stable, psycopg[binary] → pas de toolchain C
# ============================================================

FROM python:3.11-slim

# Pas de .pyc, logs en direct, pip silencieux
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances système minimales
# - curl : pour le healthcheck HTTP
# - ca-certificates : TLS propre pour httpx/requests
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les deps Python (cache-friendly)
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copier l'app
COPY ./app /app/app

# User non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Uvicorn (1 worker suffit pour l'étape 1)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
