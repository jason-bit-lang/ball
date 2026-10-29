"""IA de CVBoost (sprint 3) : jeux de donnees sans fuite, fine-tuning LoRA et evaluation SacreBLEU.

Ces scripts tournent a part (sur Google Colab ou un PC), jamais sur Render : le site n'utilise pas PyTorch.
Il lit seulement le resultat du modele, le fichier data/offres_ia.csv.

Ordre des etapes (apres celles de data_pipeline/) :
1. python -m ai_engine.etiquettes_ia     competences de chaque offre relues par gpt-4o-mini (les "corriges")
2. python -m ai_engine.prepare_dataset   jeux train / validation / test sans fuite (data/ia/)
3. python -m ai_engine.train_lora        fine-tuning LoRA de flan-t5-small (GPU conseille : Colab)
4. python -m ai_engine.evaluate_model    score SacreBLEU avec et sans LoRA, puis traitement par lot des offres
"""
