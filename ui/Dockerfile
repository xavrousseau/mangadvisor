# ============================================================
# Dockerfile — mangadvisor-ui (Streamlit)
# Rôle : UI de démonstration/admin qui consomme l'API
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances minimales : Streamlit + client HTTP
RUN pip install --no-cache-dir \
      streamlit \
      requests

# Copier l'app Streamlit (ex: app.py + assets éventuels)
COPY . /app

# User non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8501

# Lancement Streamlit : le compose définit déjà le port et l’address 0.0.0.0
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
