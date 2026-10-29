"""Copie les offres nettoyees (data/offres_propres.csv) et les resultats du modele LoRA
(data/offres_ia.csv) dans la base du site. Le site lit ensuite uniquement la base.

Pourquoi passer par la base ? Lire un fichier CSV a chaque page serait lent ; dans la base, les offres
sont retrouvees tout de suite, et les favoris et entretiens peuvent pointer vers une offre precise.
Cette copie est faite a chaque demarrage du site (run.py).
"""
import os
import pandas as pd
from data_pipeline.config import OFFRES_IA, OFFRES_PROPRES
from . import db
from .models import Offre

LIENS_AUTORISES = ('http://', 'https://', 'mailto:')  # bloque les liens "javascript:" piegés
# Colonnes copiees du fichier vers la table Offre (l'url sert de cle, elle est traitee a part)
CHAMPS = ['titre', 'entreprise', 'lieu', 'description', 'date_publication', 'date_limite', 'lien_candidature',
          'competences', 'titre_ia', 'competences_ia']


def lire_offres():
    """Offres propres + colonnes du modele LoRA si le fichier existe. Les cases vides deviennent None."""
    # Une offre sans adresse, sans titre ou sans description est inutilisable : on l'ecarte
    offres = pd.read_csv(OFFRES_PROPRES, dtype=str).dropna(subset=['url', 'titre', 'description'])
    if os.path.exists(OFFRES_IA):
        # Ajoute titre_ia et competences_ia a chaque offre, en les reliant par l'url (comme une jointure SQL)
        offres = offres.merge(pd.read_csv(OFFRES_IA, dtype=str), on='url', how='left')
    offres = offres.reindex(columns=['url'] + CHAMPS)  # garde seulement les colonnes utiles, dans cet ordre
    # Un lien qui ne commence pas par http://, https:// ou mailto: est remplace par une case vide
    for colonne in ['url', 'lien_candidature']:
        offres[colonne] = offres[colonne].where(offres[colonne].str.lower().str.startswith(LIENS_AUTORISES))
    offres = offres.dropna(subset=['url'])
    # Pandas note les cases vides "NaN" ; la base attend None. Chaque offre devient un dictionnaire.
    return offres.astype(object).where(offres.notna(), None).to_dict('records')


def synchroniser_offres():
    """Ajoute les nouvelles offres et met a jour les autres. La cle est l'adresse (url) de l'offre,
    donc les numeros des offres deja en base ne changent jamais (les favoris restent valables)."""
    if not os.path.exists(OFFRES_PROPRES):
        return 0
    existantes = {offre.url: offre for offre in Offre.query.all()}  # url -> offre deja en base
    lignes = lire_offres()
    for ligne in lignes:
        # Offre deja connue : on la met a jour ; sinon on en cree une nouvelle
        offre = existantes.get(ligne['url']) or Offre(url=ligne['url'])
        for champ in CHAMPS:
            setattr(offre, champ, ligne[champ])  # equivaut a offre.titre = ligne['titre'], etc.
        db.session.add(offre)
    db.session.commit()
    return len(lignes)
