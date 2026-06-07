# ============================================================
# Dockerfile — mangadvisor-engine (batch)
# Objectif : conteneur utilitaire pour scripts (scrape/enrich/profile)
# Étape 1 : pas de serveur uvicorn, le conteneur reste inerte
#           jusqu’à exécution d’une commande (docker exec / run)
# ============================================================

FROM python:3.11-slim

# Variables d’environnement de base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances système minimales
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copier les scripts de l’engine
COPY scripts/ ./scripts

# Créer un utilisateur non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Volume par défaut (optionnel, pratique pour échanger des données)
VOLUME ["/app/data"]

# Par défaut → conteneur inerte (batch mode)
# Cela évite l'erreur uvicorn not found.
CMD ["bash", "-lc", "sleep infinity"]
