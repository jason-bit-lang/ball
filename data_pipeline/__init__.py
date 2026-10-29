"""Donnees de CVBoost (sprint 2) : journal du site, statistiques SQL, collecte et nettoyage des offres.

Ces scripts tournent a part, jamais pendant qu'un visiteur utilise le site : ils preparent les donnees
que le site et l'IA lisent ensuite. Chaque etape se lance depuis la racine du projet.

Ordre des etapes :
1. python -m data_pipeline.logs_parser      lit le journal du site, detecte les fraudes, remplit database/analytics.db
2. python -m data_pipeline.kpi              affiche les statistiques d'usage (requetes SQL)
3. python -m data_pipeline.scraper_jobs     recupere les offres d'emploi (data/offres_brutes.csv)
4. python -m data_pipeline.pandas_cleaning  nettoie les offres pour l'IA (data/offres_propres.csv)
La suite (jeux d'entrainement, fine-tuning LoRA) est dans ai_engine/.
"""
