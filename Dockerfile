# Image de CVBoost : le site (Flask) et l'API du pitch (FastAPI) dans une seule image.
# Sur Render, demarrer.sh lance les deux. Avec docker-compose, chaque service choisit sa commande.
FROM python:3.13-slim

# Pas de fichiers .pyc, et les journaux s'affichent tout de suite
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# 1. Les bibliotheques d'abord : Docker garde cette etape en cache tant que requirements.txt ne change pas,
#    la construction suivante est donc beaucoup plus rapide
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Puis le code du projet (.dockerignore liste ce qui n'est pas copie : secrets, venv, base locale...)
COPY . .

# 3. Le site ne tourne pas en administrateur (root) : un simple utilisateur suffit
RUN useradd --create-home cvboost && chown -R cvboost /app
USER cvboost

EXPOSE 5000
CMD ["sh", "demarrer.sh"]
