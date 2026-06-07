# ============================================================
# Dockerfile — mangadvisor-scheduler (APScheduler)
# Rôle : lancer des jobs planifiés (scrapes, bootstrap embeddings, etc.)
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Outils légers utiles (health/debug + TLS)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dépendances Python (cache-friendly)
#    requirements.txt doit contenir (ex) :
#      apscheduler
#      httpx
#      psycopg[binary]
#      redis           # si tu pilotes une file via REDIS_URL
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 2) Code du scheduler
#    app.py : instancie (Async)IOScheduler, déclare tes jobs, .start()
COPY app.py ./app.py

# 3) User non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 4) Démarrage
CMD ["python", "app.py"]
