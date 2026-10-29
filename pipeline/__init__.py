"""Pipeline de donnees de CVBoost (parties 2, 3 et 5).

Ces scripts tournent a part, jamais pendant qu'un visiteur utilise le site : ils preparent les donnees
(offres, statistiques, modele d'IA) que le site lit ensuite. Chaque etape se lance depuis la racine
du projet avec "python -m pipeline.<nom>".

Ordre des etapes :
1. python -m pipeline.audit_logs        lit le journal du site, detecte les fraudes, remplit analytics.db
2. python -m pipeline.kpi               affiche les statistiques d'usage (requetes SQL)
3. python -m pipeline.scraper           recupere les offres d'emploi (data/offres_brutes.csv)
4. python -m pipeline.nettoyage_offres  nettoie les offres pour l'IA (data/offres_propres.csv)
5. python -m pipeline.dataset_ia        jeux train / validation / test sans fuite (data/ia/)
6. python -m pipeline.finetuning_lora   fine-tuning LoRA, SacreBLEU, traitement par lot (GPU : Colab)
Etapes complementaires :
- python -m pipeline.etiquettes_ia      competences de chaque offre relues par gpt-4o-mini (corriges du LoRA)
- python -m pipeline.metriques_audio    qualite des voix du pitch : WER, CER et MOS (partie 5)
"""
