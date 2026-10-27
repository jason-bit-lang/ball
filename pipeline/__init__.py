"""Pipeline de donnees de CVBoost (parties 2 et 3).

Ordre des etapes :
1. python -m pipeline.audit_logs        lit le journal du site, detecte les fraudes, remplit analytics.db
2. python -m pipeline.kpi               affiche les statistiques d'usage (requetes SQL)
3. python -m pipeline.scraper           recupere les offres d'emploi (data/offres_brutes.csv)
4. python -m pipeline.nettoyage_offres  nettoie les offres pour l'IA (data/offres_propres.csv)
5. python -m pipeline.dataset_ia        jeux train / validation / test sans fuite (data/ia/)
6. python -m pipeline.finetuning_lora   fine-tuning LoRA, SacreBLEU, traitement par lot (GPU : Colab)
"""
