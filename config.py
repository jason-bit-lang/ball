"""Reglages communs au site (Flask, dossier app/) et a l'API du pitch (FastAPI, dossier api/).

Pourquoi un fichier commun ? Le site et l'API lisent la meme base de donnees : l'adresse de la base
est donc ecrite une seule fois, ici, et les deux programmes l'importent.

Les valeurs secretes ou propres a chaque machine ne sont jamais ecrites dans le code :
- en local, elles viennent du fichier .env (copie de .env.example, jamais envoye sur GitHub) ;
- sur Render, il n'y a pas de fichier .env : elles sont saisies dans l'onglet "Environment" du service.
Dans les deux cas, le programme les lit de la meme facon avec os.environ.get().
"""
import os
from dotenv import load_dotenv

# Copie le contenu du fichier .env dans les variables d'environnement, s'il existe.
# Sur Render, ce fichier n'existe pas : load_dotenv() ne fait alors rien, et les variables
# saisies dans Render sont deja la.
load_dotenv()

# Dossier racine du projet : sert a construire des chemins qui marchent quel que soit
# le dossier depuis lequel on lance le site
DOSSIER = os.path.dirname(os.path.abspath(__file__))

# Base de donnees : Postgres sur Render (adresse donnee par DATABASE_URL), fichier SQLite en local.
# Si DATABASE_URL est absente ou vide, "or" choisit la base SQLite du dossier database/.
ADRESSE_BASE = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(DOSSIER, 'database', 'cvboost.db')

# Adresse de l'API du pitch, appelee par le site. En local et sur Render, l'API tourne sur la meme
# machine (port 8000) ; avec docker-compose, elle est dans le conteneur "api" (API_URL=http://api:8000).
ADRESSE_API = os.environ.get('API_URL', 'http://127.0.0.1:8000')
