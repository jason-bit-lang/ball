"""Chemins et reglages partages par toutes les etapes des donnees et de l'IA.

Pourquoi un seul fichier ? Si un chemin change, on le modifie ici une fois, et toutes les etapes
(data_pipeline/, ai_engine/, et le site, qui lit aussi LOG_FILE, OFFRES_PROPRES et OFFRES_IA) suivent
automatiquement.
"""
import os

# Racine du projet : le dossier au-dessus de data_pipeline/ (dirname deux fois)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')          # fichiers d'offres et jeux d'entrainement
DATABASE_DIR = os.path.join(BASE_DIR, 'database')  # bases SQLite : cvboost.db (site) et analytics.db
LOG_DIR = os.path.join(BASE_DIR, 'logs')
# Cree les dossiers s'ils n'existent pas (exist_ok=True : pas d'erreur s'ils existent deja)
for dossier in [DATA_DIR, DATABASE_DIR, LOG_DIR]:
    os.makedirs(dossier, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'evenements.log')               # ecrit par le site (app_web/journal.py)
ANALYTICS_DB = os.path.join(DATABASE_DIR, 'analytics.db')        # base des statistiques (KPI)
OFFRES_BRUTES = os.path.join(DATA_DIR, 'offres_brutes.csv')      # offres telles que le scraper les a lues
OFFRES_PROPRES = os.path.join(DATA_DIR, 'offres_propres.csv')    # offres nettoyees, copiees dans la base du site
DATASET_DIR = os.path.join(DATA_DIR, 'ia')                       # train / validation / test pour le fine-tuning
COMPETENCES_GPT = os.path.join(DATA_DIR, 'competences_gpt.csv')  # competences relues par gpt-4o-mini
OFFRES_IA = os.path.join(DATA_DIR, 'offres_ia.csv')              # resultats du modele LoRA (traitement par lot)
ADAPTATEUR_DIR = os.path.join(BASE_DIR, 'ai_engine', 'lora_cvboost')  # adaptateur LoRA entraine

# Taux de change approximatif pour convertir les salaires en francs congolais (a mettre a jour)
TAUX_CDF_USD = 2800

# Detection de fraude : au moins RAFALE_SEUIL evenements en RAFALE_MINUTES minutes
# (un humain ne rate pas 5 connexions en 10 minutes ; un robot qui essaie des mots de passe, si)
RAFALE_SEUIL = 5
RAFALE_MINUTES = 10
