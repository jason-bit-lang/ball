"""Etape 4 de ai_engine/ : evaluation du modele LoRA (SacreBLEU) puis traitement par lot des offres.

1. Evaluation : le modele lit les descriptions du jeu de test (jamais vues pendant l'entrainement) et ses
   reponses sont comparees aux reponses attendues avec SacreBLEU (0 = rien de commun, 100 = identiques).
   Le meme calcul est fait sans l'adaptateur LoRA : l'ecart montre ce que le fine-tuning a apporte.
2. Traitement par lot : le modele lit toutes les offres et ecrit data/offres_ia.csv (titre_ia et
   competences_ia), que le site copie dans sa base au demarrage. Le site n'a ainsi jamais besoin de PyTorch.

Entrees  : ai_engine/lora_cvboost/ (cree par train_lora.py), data/ia/test.jsonl, data/offres_propres.csv
Sorties  : scores ajoutes a ai_engine/lora_cvboost/scores.json ; data/offres_ia.csv
Lancement : python -m ai_engine.evaluate_model   (apres python -m ai_engine.train_lora)
"""
import json
import os
import pandas as pd
import sacrebleu
import torch
from peft import PeftModel
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from data_pipeline.config import ADAPTATEUR_DIR, DATASET_DIR, OFFRES_IA, OFFRES_PROPRES
from data_pipeline.pandas_cleaning import competences_connues
from .prepare_dataset import ENTREE_MAX as DESCRIPTION_MAX, PREFIXE
from .train_lora import ENTREE_TOKENS, MODELE, SORTIE_TOKENS, TAILLE_LOT  # memes reglages qu'a l'entrainement

FICHIER_SCORES = os.path.join(ADAPTATEUR_DIR, 'scores.json')


def charger_modele():
    """Modele de base flan-t5-small + adaptateur LoRA enregistre par train_lora.py."""
    tokenizer = AutoTokenizer.from_pretrained(ADAPTATEUR_DIR)
    modele = PeftModel.from_pretrained(AutoModelForSeq2SeqLM.from_pretrained(MODELE), ADAPTATEUR_DIR)
    return modele, tokenizer


def generer(modele, tokenizer, textes):
    """Sorties du modele pour une liste d'entrees, par lots."""
    modele.eval()  # mode utilisation (et non entrainement)
    sorties = []
    for i in range(0, len(textes), 2 * TAILLE_LOT):
        entrees = tokenizer(textes[i:i + 2 * TAILLE_LOT], max_length=ENTREE_TOKENS, truncation=True,
                            padding=True, return_tensors='pt').to(modele.device)
        with torch.no_grad():  # pas d'apprentissage ici : PyTorch n'a pas a garder de quoi corriger les poids
            ids = modele.generate(**entrees, max_new_tokens=SORTIE_TOKENS)
        sorties += tokenizer.batch_decode(ids, skip_special_tokens=True)
    return [sortie.strip() for sortie in sorties]


def score_sacrebleu(modele, tokenizer, test):
    """SacreBLEU des reponses du modele sur le jeu de test."""
    predictions = generer(modele, tokenizer, list(test['entree']))
    return sacrebleu.corpus_bleu(predictions, [list(test['sortie'])]).score, predictions


def lire_sortie(sortie):
    """'Poste : X | Competences : a, b' -> ('X', 'a, b').
    Seules les competences connues sont gardees, sans doublon : un petit modele invente parfois
    des mots ("sant", "luz") ou repete une competence."""
    # partition coupe le texte en trois : avant le separateur, le separateur, apres
    poste, _, competences = sortie.partition('| Competences :')
    return poste.replace('Poste :', '').strip(), competences_connues(competences.split(','))


def traiter_offres(modele, tokenizer):
    """Traitement par lot : le modele lit toutes les offres. Le site lira ensuite data/offres_ia.csv."""
    offres = pd.read_csv(OFFRES_PROPRES).dropna(subset=['url', 'description'])
    sorties = generer(modele, tokenizer, [PREFIXE + d[:DESCRIPTION_MAX] for d in offres['description']])
    resultats = [lire_sortie(sortie) for sortie in sorties]
    offres_ia = pd.DataFrame({'url': offres['url'],
                              'titre_ia': [titre for titre, _ in resultats],
                              'competences_ia': [competences for _, competences in resultats]})
    offres_ia.to_csv(OFFRES_IA, index=False)
    return len(offres_ia)


def main():
    """Score SacreBLEU avec et sans LoRA, quelques exemples, puis traitement par lot des offres."""
    modele, tokenizer = charger_modele()
    test = pd.read_json(os.path.join(DATASET_DIR, 'test.jsonl'), lines=True)  # un exemple JSON par ligne

    score_lora, predictions = score_sacrebleu(modele, tokenizer, test)
    with modele.disable_adapter():  # meme modele, adaptateur LoRA debranche : le point de comparaison
        score_base, _ = score_sacrebleu(modele, tokenizer, test)
    print(f'SacreBLEU test - modele de base : {score_base:.1f}')
    print(f'SacreBLEU test - avec LoRA      : {score_lora:.1f}\n')
    for attendu, obtenu in list(zip(test['sortie'], predictions))[:3]:
        print('Attendu :', attendu)
        print('Modele  :', obtenu, '\n')

    # Les scores sont ajoutes aux informations de l'entrainement (fichier ecrit par train_lora.py)
    scores = {}
    if os.path.exists(FICHIER_SCORES):
        with open(FICHIER_SCORES) as fichier:
            scores = json.load(fichier)
    scores.update(sacrebleu_base=round(score_base, 2), sacrebleu_lora=round(score_lora, 2), exemples_test=len(test))
    with open(FICHIER_SCORES, 'w') as fichier:
        json.dump(scores, fichier, indent=2)

    print(f'{traiter_offres(modele, tokenizer)} offres traitees : {OFFRES_IA}')


if __name__ == '__main__':
    main()
