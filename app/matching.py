"""Moteur de matching : compare le texte du CV a toutes les offres avec TF-IDF (scikit-learn).

TF-IDF donne du poids aux mots rares et propres a une offre ("comptable", "django"),
et presque aucun aux mots presents partout ("candidature", "poste").
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pipeline.nettoyage_offres import normaliser, trouver_competences
from . import db
from .affichage import est_close
from .models import Offre

NOMBRE_RESULTATS = 10
POIDS_ENTETE = 3  # le titre et les competences comptent 3 fois plus que la description
# Niveaux affiches a la place du score : compares a la meilleure offre trouvee pour ce CV
SCORE_MIN = 5            # si la meilleure offre est sous 5 %, aucune n'est dite proche
PART_TRES_PROCHE = 0.75  # au moins 75 % du meilleur score
PART_PROCHE = 0.45       # au moins 45 % du meilleur score

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


def niveau(score, meilleur):
    """'tres-proche', 'proche' ou 'explorer' : plus parlant pour l'utilisateur qu'un pourcentage."""
    if meilleur >= SCORE_MIN and score >= PART_TRES_PROCHE * meilleur:
        return 'tres-proche'
    if meilleur >= SCORE_MIN and score >= PART_PROCHE * meilleur:
        return 'proche'
    return 'explorer'


def comparer(offre, competences_cv, score=0):
    """Competences en commun avec le CV (atouts) et competences de l'offre absentes du CV (a renforcer)."""
    competences_offre = liste(offre.competences) | liste(offre.competences_ia)
    return {'offre': offre, 'score': score, 'niveau': 'explorer',
            'communes': sorted(competences_cv & competences_offre),
            'renforcer': sorted(competences_offre - competences_cv)}


def scores_du_cv(texte_cv):
    """Similarite (cosinus TF-IDF) du CV avec chaque offre de l'index, dans l'ordre de index['ids']."""
    index = index_offres()
    if index is None:
        return None, []
    vecteur_cv = index['vectoriseur'].transform([normaliser(texte_cv)])
    return index, cosine_similarity(vecteur_cv, index['matrice'])[0]


def rechercher(texte_cv, nombre=NOMBRE_RESULTATS):
    """Offres encore ouvertes les plus proches du CV, de la plus proche a la moins proche.
    Liste vide si le CV n'a aucun mot en commun avec les offres."""
    index, scores = scores_du_cv(texte_cv)
    if index is None:
        return []
    competences_cv = set(trouver_competences(texte_cv))

    resultats = []
    for position in scores.argsort()[::-1]:
        if scores[position] <= 0 or len(resultats) == nombre:
            break
        offre = db.session.get(Offre, index['ids'][position])
        if not est_close(offre):  # on ne propose pas une offre dont la date limite est passee
            resultats.append(comparer(offre, competences_cv, round(scores[position] * 100)))
    for resultat in resultats:
        resultat['niveau'] = niveau(resultat['score'], resultats[0]['score'])
    return resultats


def offres_recentes(texte_cv, nombre=NOMBRE_RESULTATS):
    """Quand aucune offre n'a de point commun avec le CV : on propose quand meme les plus recentes."""
    competences_cv = set(trouver_competences(texte_cv))
    offres = Offre.query.order_by(Offre.date_publication.desc()).all()
    ouvertes = [offre for offre in offres if not est_close(offre)]
    return [comparer(offre, competences_cv) for offre in ouvertes[:nombre]]


def cv_reconnu(texte_cv):
    """Faux seulement si rien n'est reconnu dans le CV : aucune competence et aucun mot en commun avec les offres."""
    index, scores = scores_du_cv(texte_cv)
    return bool(trouver_competences(texte_cv)) or (index is not None and scores.max() > 0)
