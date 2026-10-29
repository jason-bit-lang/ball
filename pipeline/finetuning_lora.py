"""Etape 6 : fine-tuning LoRA de flan-t5-small, evaluation SacreBLEU et traitement par lot des offres.

Tache apprise : description d'une offre -> "Poste : ... | Competences : ..." (voir pipeline/dataset_ia.py).
LoRA garde les poids du modele geles et n'entraine que deux petites matrices ajoutees a cote des
matrices d'attention requete et valeur (appelees `q` et `v` dans T5, `q_proj` et `v_proj` ailleurs).
Pourquoi LoRA ? Entrainer tout le modele demanderait beaucoup de memoire et produirait un fichier de
300 Mo ; avec LoRA, moins de 1 % des parametres bougent et l'adaptateur ne pese que 1,4 Mo.

Entrees  : data/ia/train.jsonl, validation.jsonl, test.jsonl ; data/offres_propres.csv
Sorties  : modele/lora_cvboost/ (adaptateur LoRA + scores.json) ; data/offres_ia.csv
Lancement : pip install -r requirements-ia.txt puis python -m pipeline.finetuning_lora
            (GPU conseille : Google Colab, voir notebooks/finetuning_lora.ipynb)
Ce script n'est jamais charge par le site : PyTorch n'est pas necessaire sur Render.
"""
import json
import os
import sys
import tempfile
import numpy as np
import pandas as pd
import sacrebleu
import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq, Seq2SeqTrainer,
                          Seq2SeqTrainingArguments, set_seed)
from .config import ADAPTATEUR_DIR, DATASET_DIR, OFFRES_IA, OFFRES_PROPRES
from .dataset_ia import ENTREE_MAX as DESCRIPTION_MAX, PARTS, PREFIXE
from .nettoyage_offres import competences_connues

MODELE = 'google/flan-t5-small'
ENTREE_TOKENS, SORTIE_TOKENS = 512, 64  # longueurs maximales en tokens (un token = un morceau de mot)
EPOQUES = 20                            # peu d'exemples : on les revoit plusieurs fois
TAILLE_LOT = 8                          # exemples traites ensemble a chaque pas d'apprentissage

# Reglages LoRA
CONFIG_LORA = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=8,                        # taille des petites matrices ajoutees
    lora_alpha=16,              # force de l'adaptation
    lora_dropout=0.05,          # coupe au hasard 5 % des liaisons pendant l'entrainement : evite le "par coeur"
    target_modules=['q', 'v'],  # projections requete et valeur (q_proj / v_proj)
)


def charger_jeux():
    """Charge les trois jeux et reverifie qu'aucune offre n'est partagee entre deux jeux."""
    # load_dataset (Hugging Face) lit les fichiers JSONL crees par pipeline/dataset_ia.py
    jeux = load_dataset('json', data_files={nom: os.path.join(DATASET_DIR, f'{nom}.jsonl') for nom in PARTS})
    empreintes = {nom: set(jeux[nom]['hash']) for nom in jeux}
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not empreintes[a] & empreintes[b], f'fuite entre {a} et {b}'
    return jeux


def tokeniser(tokenizer, jeux):
    """Transforme les textes en suites de nombres (tokens) que le modele sait lire."""
    def lot(exemples):
        # Entree (description) et sortie attendue ("labels") sont toutes deux transformees en tokens
        entrees = tokenizer(exemples['entree'], max_length=ENTREE_TOKENS, truncation=True)
        entrees['labels'] = tokenizer(text_target=exemples['sortie'], max_length=SORTIE_TOKENS,
                                      truncation=True)['input_ids']
        return entrees
    # batched=True : les exemples sont traites par paquets (plus rapide) ; les colonnes texte ne servent plus
    return jeux.map(lot, batched=True, remove_columns=jeux['train'].column_names)


def creer_trainer(modele, tokenizer, jeux_tokens, dossier, epoques):
    """Prepare l'entrainement (Seq2SeqTrainer de Hugging Face) et le calcul du score SacreBLEU."""
    def decoder(ids):
        """Tokens -> textes lisibles."""
        ids = np.where(ids != -100, ids, tokenizer.pad_token_id)  # -100 = case vide a ignorer
        return [texte.strip() for texte in tokenizer.batch_decode(ids, skip_special_tokens=True)]

    def calculer_bleu(prediction):
        """SacreBLEU compare les textes produits aux textes attendus : 0 = rien de commun, 100 = identiques."""
        predictions, references = decoder(prediction.predictions), decoder(prediction.label_ids)
        return {'bleu': sacrebleu.corpus_bleu(predictions, [references]).score}

    arguments = Seq2SeqTrainingArguments(
        output_dir=dossier,
        num_train_epochs=epoques,
        learning_rate=1e-3,                # LoRA supporte un pas plus grand qu'un fine-tuning complet
        per_device_train_batch_size=TAILLE_LOT,
        per_device_eval_batch_size=TAILLE_LOT,
        eval_strategy='epoch',
        save_strategy='epoch',
        save_total_limit=1,
        load_best_model_at_end=True,       # garde l'epoque qui a le meilleur BLEU en validation
        metric_for_best_model='bleu',
        predict_with_generate=True,
        generation_max_length=SORTIE_TOKENS,
        fp16=False,                        # T5 est instable en demi-precision
        logging_steps=10,
        report_to='none',
    )
    return Seq2SeqTrainer(
        model=modele,
        args=arguments,
        train_dataset=jeux_tokens['train'],
        eval_dataset=jeux_tokens['validation'],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=modele),
        tokenizer=tokenizer,
        compute_metrics=calculer_bleu,
    )


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
    return sorties


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


def main(epoques=EPOQUES):
    """Entrainement, evaluation avec et sans LoRA, enregistrement de l'adaptateur, puis traitement par lot."""
    set_seed(42)  # memes resultats d'un lancement a l'autre
    print('Materiel :', 'GPU ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'processeur (CPU)')
    jeux = charger_jeux()
    print('Aucune fuite entre les jeux :', {nom: len(jeux[nom]) for nom in jeux})

    tokenizer = AutoTokenizer.from_pretrained(MODELE)
    modele = get_peft_model(AutoModelForSeq2SeqLM.from_pretrained(MODELE), CONFIG_LORA)
    modele.print_trainable_parameters()  # moins de 1 % des parametres sont entraines

    jeux_tokens = tokeniser(tokenizer, jeux)
    with tempfile.TemporaryDirectory() as dossier:  # sauvegardes intermediaires, effacees a la fin
        trainer = creer_trainer(modele, tokenizer, jeux_tokens, dossier, epoques)
        trainer.train()
        # Score final sur le jeu de test, jamais vu pendant l'entrainement, avec et sans LoRA
        score_lora = trainer.evaluate(jeux_tokens['test'], metric_key_prefix='test')['test_bleu']
        with modele.disable_adapter():  # meme modele, adaptateur LoRA debranche : le point de comparaison
            score_base = trainer.evaluate(jeux_tokens['test'], metric_key_prefix='test')['test_bleu']
    print(f'SacreBLEU test - modele de base : {score_base:.1f}')
    print(f'SacreBLEU test - avec LoRA      : {score_lora:.1f}')

    exemples = jeux['test'].select(range(3))
    for exemple, sortie in zip(exemples, generer(modele, tokenizer, exemples['entree'])):
        print('Attendu :', exemple['sortie'])
        print('Modele  :', sortie, '\n')

    modele.save_pretrained(ADAPTATEUR_DIR)  # enregistre uniquement l'adaptateur LoRA (quelques Mo)
    tokenizer.save_pretrained(ADAPTATEUR_DIR)
    scores = {'modele': MODELE, 'epoques': epoques,
              'sacrebleu_base': round(score_base, 2), 'sacrebleu_lora': round(score_lora, 2),
              'exemples_train': len(jeux['train']), 'exemples_validation': len(jeux['validation']),
              'exemples_test': len(jeux['test'])}
    with open(os.path.join(ADAPTATEUR_DIR, 'scores.json'), 'w') as fichier:
        json.dump(scores, fichier, indent=2)
    print(f'Adaptateur enregistre dans : {ADAPTATEUR_DIR}')
    print(f'{traiter_offres(modele, tokenizer)} offres traitees : {OFFRES_IA}')


# "python -m pipeline.finetuning_lora 2" : 2 epoques seulement (essai rapide) ; 20 sinon
if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else EPOQUES)
