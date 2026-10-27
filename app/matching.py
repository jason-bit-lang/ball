"""Moteur de matching : compare le texte du CV a toutes les offres avec TF-IDF (scikit-learn).

TF-IDF donne du poids aux mots rares et propres a une offre ("comptable", "django"),
et presque aucun aux mots presents partout ("candidature", "poste").
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pipeline.nettoyage_offres import normaliser, trouver_competences
from . import db
from .models import Offre

NOMBRE_RESULTATS = 10
POIDS_ENTETE = 3  # le titre et les competences comptent 3 fois plus que la description

# Le calcul de l'index prend du temps : il est fait une seule fois puis garde en memoire
_index = {}


def liste(texte):
    """'a, b' -> {'a', 'b'}"""
    return {mot.strip() for mot in (texte or '').split(',') if mot.strip()}


def texte_offre(offre):
    """Texte compare au CV. Le titre et les competences trouves par le modele LoRA y sont ajoutes."""
    entete = ' '.join(filter(None, [offre.titre, offre.titre_ia, offre.competences, offre.competences_ia]))
    return normaliser((entete + ' ') * POIDS_ENTETE + offre.description)


def index_offres():
    """Vectoriseur et matrice TF-IDF des offres, recalcules seulement si les offres ont change."""
    offres = Offre.query.order_by(Offre.id).all()
    cle = (len(offres), offres[-1].id if offres else 0)
    if offres and _index.get('cle') != cle:
        # max_df=0.5 : un mot present dans plus de la moitie des offres est ignore
        vectoriseur = TfidfVectorizer(sublinear_tf=True, max_df=0.5, ngram_range=(1, 2))
        matrice = vectoriseur.fit_transform([texte_offre(offre) for offre in offres])
        _index.update(cle=cle, ids=[offre.id for offre in offres], vectoriseur=vectoriseur, matrice=matrice)
    return _index if offres else None


def rechercher(texte_cv, nombre=NOMBRE_RESULTATS):
    """Renvoie les offres les plus proches du CV : [{'offre', 'score', 'communes'}, ...]"""
    index = index_offres()
    if index is None:
        return []
    vecteur_cv = index['vectoriseur'].transform([normaliser(texte_cv)])
    scores = cosine_similarity(vecteur_cv, index['matrice'])[0]
    competences_cv = set(trouver_competences(texte_cv))

    resultats = []
    for position in scores.argsort()[::-1][:nombre]:
        if scores[position] <= 0:
            break
        offre = db.session.get(Offre, index['ids'][position])
        communes = competences_cv & (liste(offre.competences) | liste(offre.competences_ia))
        resultats.append({'offre': offre, 'score': round(scores[position] * 100), 'communes': sorted(communes)})
    return resultats
