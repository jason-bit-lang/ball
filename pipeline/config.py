"""Chemins et reglages partages par toutes les etapes du pipeline."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'evenements.log')        # ecrit par le site (app/journal.py)
ANALYTICS_DB = os.path.join(DATA_DIR, 'analytics.db')     # base des statistiques
OFFRES_BRUTES = os.path.join(DATA_DIR, 'offres_brutes.csv')
OFFRES_PROPRES = os.path.join(DATA_DIR, 'offres_propres.csv')
DATASET_DIR = os.path.join(DATA_DIR, 'ia')                 # train / validation / test pour le fine-tuning
OFFRES_IA = os.path.join(DATA_DIR, 'offres_ia.csv')        # resultats du modele LoRA (crees sur Colab)

# Taux de change approximatif pour convertir les salaires en francs congolais (a mettre a jour)
TAUX_CDF_USD = 2800

# Detection de fraude : au moins RAFALE_SEUIL evenements en RAFALE_MINUTES minutes
RAFALE_SEUIL = 5
RAFALE_MINUTES = 10
