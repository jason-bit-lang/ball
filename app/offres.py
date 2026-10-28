"""Copie les offres nettoyees (data/offres_propres.csv) et les resultats du modele LoRA
(data/offres_ia.csv) dans la base du site. Le site lit ensuite uniquement la base."""
import os
import pandas as pd
from pipeline.config import OFFRES_IA, OFFRES_PROPRES
from . import db
from .models import Offre

LIENS_AUTORISES = ('http://', 'https://', 'mailto:')  # bloque les liens "javascript:" piegés
CHAMPS = ['titre', 'entreprise', 'lieu', 'description', 'date_publication', 'date_limite', 'lien_candidature',
          'competences', 'titre_ia', 'competences_ia']


def lire_offres():
    """Offres propres + colonnes du modele LoRA si le fichier existe. Les cases vides deviennent None."""
    offres = pd.read_csv(OFFRES_PROPRES, dtype=str).dropna(subset=['url', 'titre', 'description'])
    if os.path.exists(OFFRES_IA):
        offres = offres.merge(pd.read_csv(OFFRES_IA, dtype=str), on='url', how='left')
    offres = offres.reindex(columns=['url'] + CHAMPS)
    for colonne in ['url', 'lien_candidature']:
        offres[colonne] = offres[colonne].where(offres[colonne].str.lower().str.startswith(LIENS_AUTORISES))
    offres = offres.dropna(subset=['url'])
    return offres.astype(object).where(offres.notna(), None).to_dict('records')


def synchroniser_offres():
    """Ajoute les nouvelles offres et met a jour les autres. La cle est l'adresse (url) de l'offre,
    donc les numeros des offres deja en base ne changent jamais."""
    if not os.path.exists(OFFRES_PROPRES):
        return 0
    existantes = {offre.url: offre for offre in Offre.query.all()}
    lignes = lire_offres()
    for ligne in lignes:
        offre = existantes.get(ligne['url']) or Offre(url=ligne['url'])
        for champ in CHAMPS:
            setattr(offre, champ, ligne[champ])
        db.session.add(offre)
    db.session.commit()
    return len(lignes)
