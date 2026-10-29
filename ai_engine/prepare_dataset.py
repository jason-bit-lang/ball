"""Etape 5 : prepare le jeu de donnees du fine-tuning LoRA, sans fuite entre train, validation et test.

Tache apprise par le modele : description d'une offre -> intitule du poste et competences.
  entree : "Extraire le poste et les competences : <debut de la description>"
  sortie : "Poste : Comptable | Competences : comptabilite, bureautique"

Anti-fuite :
1. Empreinte SHA-256 de chaque entree : deux offres identiques n'en font plus qu'une.
2. Les quasi-doublons (meme annonce publiee pour deux provinces, par exemple) sont aussi retires,
   sinon le modele serait teste sur un texte qu'il a deja vu pendant l'entrainement.
3. Separation 80 / 10 / 10 selon l'empreinte : une offre tombe toujours dans le meme jeu.
4. Des assertions verifient automatiquement qu'aucune offre n'est dans deux jeux a la fois.

Entree  : data/offres_propres.csv (+ data/competences_gpt.csv s'il existe : competences relues par
          gpt-4o-mini, plus justes que celles des mots-cles ; voir ai_engine/etiquettes_ia.py)
Sorties : data/ia/train.jsonl, data/ia/validation.jsonl, data/ia/test.jsonl
Lancement : python -m ai_engine.prepare_dataset
"""
import hashlib
import os
import pandas as pd
from data_pipeline.config import COMPETENCES_GPT, DATASET_DIR, OFFRES_PROPRES
from data_pipeline.pandas_cleaning import normaliser

PREFIXE = 'Extraire le poste et les competences : '
ENTREE_MAX = 2000        # caracteres gardes (flan-t5-small lit au plus 512 tokens)
SIMILARITE_MAX = 0.8     # au-dela, deux descriptions sont considerees comme la meme annonce
# train : pour apprendre ; validation : pour suivre l'apprentissage ; test : pour la note finale (jamais vu avant)
PARTS = {'train': 0.8, 'validation': 0.1, 'test': 0.1}


def creer_exemple(titre, competences, description):
    """Transforme une offre en couple (entree, sortie) pour le modele."""
    # Une offre sans competence trouvee recoit "aucune" : le modele apprend aussi ce cas
    competences = competences if isinstance(competences, str) and competences else 'aucune'
    return {'entree': PREFIXE + str(description)[:ENTREE_MAX],
            'sortie': f'Poste : {titre} | Competences : {competences}'}


def empreinte(texte):
    """SHA-256 du texte normalise : les differences d'accents ou d'espaces ne comptent pas.
    Une empreinte est une suite de 64 caracteres qui change completement si le texte change d'une lettre :
    deux textes identiques ont toujours la meme empreinte."""
    return hashlib.sha256(normaliser(texte).encode()).hexdigest()


def trigrammes(texte):
    """Ensemble des suites de 3 mots du texte, pour comparer deux descriptions."""
    mots = normaliser(texte).split()
    # "un deux trois quatre" -> {"un deux trois", "deux trois quatre"}
    return {' '.join(mots[i:i + 3]) for i in range(len(mots) - 2)}


def similarite(a, b):
    """Indice de Jaccard : part des trigrammes communs (0 = rien en commun, 1 = identiques)."""
    return len(a & b) / len(a | b) if a and b else 0  # communs / tous (& : intersection, | : union)


def retirer_quasi_doublons(df):
    """Garde la premiere offre de chaque groupe de descriptions presque identiques."""
    gardees, vus = [], []  # numeros des offres gardees, et leurs trigrammes
    for index, description in df['description'].items():
        t = trigrammes(description)
        # L'offre est gardee seulement si elle ne ressemble a aucune offre deja gardee
        if all(similarite(t, autre) < SIMILARITE_MAX for autre in vus):
            gardees.append(index)
            vus.append(t)
    return df.loc[gardees]


def separer(df):
    """Trie les offres par empreinte (ordre stable et sans biais) puis coupe en 80 / 10 / 10.
    Trier par empreinte melange les offres comme un tirage au sort, mais donne toujours le meme resultat :
    relancer le script ne fait jamais passer une offre du jeu de test au jeu d'entrainement."""
    df = df.sort_values('hash').reset_index(drop=True)
    n_train = round(len(df) * PARTS['train'])
    n_validation = round(len(df) * PARTS['validation'])
    return {'train': df[:n_train],
            'validation': df[n_train:n_train + n_validation],
            'test': df[n_train + n_validation:]}


def verifier(jeux, total):
    """Assertions anti-fuite : le script s'arrete avec une erreur si l'une d'elles est fausse."""
    hashes = {nom: set(jeu['hash']) for nom, jeu in jeux.items()}  # empreintes de chaque jeu
    assert sum(len(jeu) for jeu in jeux.values()) == total, 'des offres ont ete perdues'
    for nom, jeu in jeux.items():
        assert len(hashes[nom]) == len(jeu), f'doublon a l\'interieur de {nom}'
        assert abs(len(jeu) - total * PARTS[nom]) <= 1, f'{nom} ne respecte pas la proportion prevue'
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not hashes[a] & hashes[b], f'fuite : meme offre dans {a} et {b}'
        # Aucun texte du jeu b ne doit ressembler a un texte du jeu a
        textes_a = [trigrammes(d) for d in jeux[a]['description']]
        for d in jeux[b]['description']:
            t = trigrammes(d)
            assert all(similarite(t, autre) < SIMILARITE_MAX for autre in textes_a), \
                f'fuite : quasi-doublon entre {a} et {b}'


def preparer(offres):
    """Renvoie les trois jeux et un resume chiffre."""
    resume = {'offres': len(offres)}
    if os.path.exists(COMPETENCES_GPT):
        # Competences relues par gpt-4o-mini quand elles existent, sinon celles des mots-cles
        gpt = pd.read_csv(COMPETENCES_GPT).dropna(subset=['competences_gpt'])
        offres = offres.merge(gpt, on='url', how='left')
        offres['competences'] = offres['competences_gpt'].fillna(offres['competences'])
        resume['competences_gpt'] = int(offres['competences_gpt'].notna().sum())
    df = offres[['titre', 'competences', 'description']].dropna(subset=['titre', 'description']).copy()
    df['hash'] = df['description'].map(empreinte)

    # Anti-fuite, etapes 1 et 2 : doublons exacts puis quasi-doublons
    avant = len(df)
    df = df.drop_duplicates(subset='hash')
    resume['doublons_exacts'] = avant - len(df)
    avant = len(df)
    df = retirer_quasi_doublons(df)
    resume['quasi_doublons'] = avant - len(df)

    # Etapes 3 et 4 : separation 80/10/10 puis assertions
    jeux = separer(df)
    verifier(jeux, len(df))
    resume.update({nom: len(jeu) for nom, jeu in jeux.items()})
    return jeux, resume


def main():
    """Prepare les trois jeux et les enregistre au format JSONL (un exemple JSON par ligne)."""
    try:
        offres = pd.read_csv(OFFRES_PROPRES)
    except FileNotFoundError:
        print(f'Fichier introuvable : {OFFRES_PROPRES}. Lancez d\'abord : python -m data_pipeline.pandas_cleaning')
        return
    jeux, resume = preparer(offres)
    os.makedirs(DATASET_DIR, exist_ok=True)
    for nom, jeu in jeux.items():
        exemples = pd.DataFrame([creer_exemple(t, c, d) for t, c, d
                                 in zip(jeu['titre'], jeu['competences'], jeu['description'])])
        exemples['hash'] = jeu['hash'].values  # l'empreinte reste dans le fichier : on peut reverifier la separation
        exemples.to_json(os.path.join(DATASET_DIR, f'{nom}.jsonl'), orient='records', lines=True,
                         force_ascii=False)
    for etape, nombre in resume.items():
        print(f'{etape:18} {nombre}')
    print('Assertions anti-fuite : OK')
    print(f'Fichiers crees dans : {DATASET_DIR}')


if __name__ == '__main__':
    main()
