"""Reglages communs au site (Flask, dossier app/) et a l'API du pitch (FastAPI, dossier api/).
Les valeurs secretes ou propres a chaque machine viennent du fichier .env (en local)
ou des variables d'environnement (sur Render)."""
import os
from dotenv import load_dotenv

load_dotenv()

DOSSIER = os.path.dirname(os.path.abspath(__file__))  # racine du projet

# Base de donnees : Postgres sur Render (adresse donnee par DATABASE_URL), fichier SQLite en local
ADRESSE_BASE = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(DOSSIER, 'database', 'cvboost.db')

# Adresse de l'API du pitch, appelee par le site (en local et sur Render : meme machine, port 8000)
ADRESSE_API = os.environ.get('API_URL', 'http://127.0.0.1:8000')
