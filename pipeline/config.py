"""Chemins et reglages partages par toutes les etapes du pipeline.

Pourquoi un seul fichier ? Si un chemin change, on le modifie ici une fois, et toutes les etapes
(et le site, qui lit aussi LOG_FILE, OFFRES_PROPRES et OFFRES_IA) suivent automatiquement.
"""
import os

# Racine du projet : le dossier au-dessus de pipeline/ (dirname deux fois)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
# Cree les dossiers s'ils n'existent pas (exist_ok=True : pas d'erreur s'ils existent deja)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'evenements.log')        # ecrit par le site (app/journal.py)
ANALYTICS_DB = os.path.join(DATA_DIR, 'analytics.db')     # base des statistiques
OFFRES_BRUTES = os.path.join(DATA_DIR, 'offres_brutes.csv')    # offres telles que le scraper les a lues
OFFRES_PROPRES = os.path.join(DATA_DIR, 'offres_propres.csv')  # offres nettoyees, copiees dans la base du site
DATASET_DIR = os.path.join(DATA_DIR, 'ia')                 # train / validation / test pour le fine-tuning
COMPETENCES_GPT = os.path.join(DATA_DIR, 'competences_gpt.csv')  # competences relues par gpt-4o-mini
OFFRES_IA = os.path.join(DATA_DIR, 'offres_ia.csv')        # resultats du modele LoRA (crees sur Colab)
ADAPTATEUR_DIR = os.path.join(BASE_DIR, 'modele', 'lora_cvboost')  # adaptateur LoRA entraine

# Taux de change approximatif pour convertir les salaires en francs congolais (a mettre a jour)
TAUX_CDF_USD = 2800

# Detection de fraude : au moins RAFALE_SEUIL evenements en RAFALE_MINUTES minutes
# (un humain ne rate pas 5 connexions en 10 minutes ; un robot qui essaie des mots de passe, si)
RAFALE_SEUIL = 5
RAFALE_MINUTES = 10
