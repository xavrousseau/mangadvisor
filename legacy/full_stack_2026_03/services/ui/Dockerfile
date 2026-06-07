# ============================================================
# Dockerfile — mangadvisor-ui (NiceGUI)
# Étape 1 : lean, WS-ready, sans toolchain C
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl + certs (healthcheck, TLS)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances (cache-friendly)
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Code UI
COPY app.py ./app.py

# User non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Démarrage NiceGUI
CMD ["python", "app.py"]
