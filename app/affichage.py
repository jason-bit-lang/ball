"""Petites fonctions de mise en forme pour les pages : dates en francais, noms des competences,
echeance d'une offre, annonce decoupee en sections, maniere de postuler.
Elles sont aussi disponibles dans les gabarits Jinja comme filtres : {{ offre.date_publication | date_fr }}."""
import re
from datetime import date, datetime
from . import app

MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre',
        'novembre', 'décembre']
JOURS_BIENTOT = 7     # en dessous, la date de cloture est signalee en jaune
JOURS_NOUVELLE = 7    # une offre publiee depuis moins de 7 jours porte le badge "Nouvelle"

# Les competences sont enregistrees sans accents (comptabilite) : voici leur nom a afficher
NOMS_COMPETENCES = {
    'python': 'Python', 'javascript': 'JavaScript', 'php': 'PHP', 'java': 'Java', 'web': 'Développement web',
    'sql': 'SQL', 'reseaux': 'Réseaux', 'donnees': 'Données', 'bureautique': 'Bureautique',
    'comptabilite': 'Comptabilité', 'finance': 'Finance', 'gestion_projet': 'Gestion de projet',
    'suivi_evaluation': 'Suivi-évaluation', 'rh': 'Ressources humaines', 'logistique': 'Logistique',
    'commercial': 'Commercial', 'marketing': 'Marketing', 'juridique': 'Juridique', 'sante': 'Santé',
    'enseignement': 'Enseignement', 'ingenierie': 'Ingénierie', 'environnement': 'Environnement',
    'agriculture': 'Agriculture', 'qualite_laboratoire': 'Qualité et laboratoire', 'securite': 'Sécurité',
    'chauffeur': 'Conduite', 'anglais': 'Anglais', 'langues_locales': 'Langues locales',
}

# Decoupage d'une annonce. Un titre de section est : un numero suivi de MAJUSCULES ("3 TACHES ET
# RESPONSABILITES"), ou un mot connu suivi de deux-points ("Responsabilites :"). Une puce est "+", "*", "»" ou ">".
MOTS_TITRES = (r"r[ée]sum[ée] du poste|contexte|responsabilit[ée]s|t[aâ]ches et responsabilit[ée]s|t[aâ]ches|"
               r"missions?|profil(?: recherch[ée])?|comp[ée]tences(?: de base| requises)?|"
               r"qualifications?(?: et exp[ée]riences?)?|formation ?& ?exp[ée]rience|exp[ée]riences?|"
               r"qualit[ée]s requises|langues|informatique|dossier de candidature|comment postuler|"
               r"position organisationnelle|crit[eè]res minima de recrutement")
TITRE_REGEX = re.compile(r"\b\d{1,2}\s?[.)]?\s+([A-ZÉÈÀ][A-ZÉÈÀ'&, ]{4,38}[A-ZÉÈÀ])(?=\s)|\b(?i:(" + MOTS_TITRES + r"))\s*:")
# Les titres en MAJUSCULES des annonces scannees n'ont pas d'accents : on remet ceux des mots frequents
ACCENTS = {'taches': 'tâches', 'responsabilites': 'responsabilités', 'competences': 'compétences',
           'experiences': 'expériences', 'experience': 'expérience', 'qualites': 'qualités', 'criteres': 'critères',
           'duree': 'durée', 'delai': 'délai', 'hierarchiques': 'hiérarchiques', 'evaluation': 'évaluation',
           'resume': 'résumé', 'generalites': 'généralités', 'specifiques': 'spécifiques'}
PUCE_REGEX = re.compile(r"\s[+*»>]_?\s")
PHRASES_PAR_PARAGRAPHE = 3


def en_date(valeur):
    """'2026-10-07' (texte) ou une date -> objet date. None si vide."""
    if not valeur:
        return None
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    return date.fromisoformat(str(valeur)[:10])


@app.template_filter('date_fr')
def date_fr(valeur):
    """'2026-10-07' -> '7 octobre 2026'"""
    jour = en_date(valeur)
    return f'{jour.day} {MOIS[jour.month - 1]} {jour.year}' if jour else ''


@app.template_filter('competence')
def competence(nom):
    """'comptabilite' -> 'Comptabilité'"""
    return NOMS_COMPETENCES.get(nom, nom.capitalize())


@app.template_global()
def est_nouvelle(offre):
    publication = en_date(offre.date_publication)
    return publication is not None and (date.today() - publication).days < JOURS_NOUVELLE


def est_close(offre):
    limite = en_date(offre.date_limite)
    return limite is not None and limite < date.today()


def echeance(offre):
    """Date de cloture d'une offre, prete a afficher : texte, classe du badge, etiquette et part du temps ecoule."""
    limite = en_date(offre.date_limite)
    if limite is None:
        return {'texte': 'Date limite non précisée', 'classe': 'inconnue', 'etiquette': '', 'part': 0}
    restants = (limite - date.today()).days
    texte = 'Clôture le ' + date_fr(limite)
    if restants < 0:
        return {'texte': texte, 'classe': 'close', 'etiquette': 'Clôturée', 'part': 100}
    publication = en_date(offre.date_publication) or date.today()
    total = max((limite - publication).days, 1)
    part = min(100, round((total - restants) / total * 100))
    if restants == 0:
        etiquette = "Dernier jour"
    elif restants <= JOURS_BIENTOT:
        etiquette = f'Plus que {restants} jour' + ('s' if restants > 1 else '')
    else:
        etiquette = f'{restants} jours restants'
    classe = 'bientot' if restants <= JOURS_BIENTOT else 'ouverte'
    return {'texte': texte, 'classe': classe, 'etiquette': etiquette, 'part': part}


def paragraphes(texte):
    """Texte sans titres : coupe en paragraphes de quelques phrases pour qu'il reste lisible."""
    phrases = re.split(r'(?<=[.!?])\s+(?=[A-ZÉÈÀ])', texte)
    return [' '.join(phrases[i:i + PHRASES_PAR_PARAGRAPHE]) for i in range(0, len(phrases), PHRASES_PAR_PARAGRAPHE)]


def decouper_description(texte):
    """Annonce lue en un seul bloc (OCR) -> [{'titre', 'puces', 'paragraphes'}, ...].
    La premiere section (avant le premier titre) n'a pas de titre."""
    sections = []
    titre = ''
    debut = 0
    for trouve in TITRE_REGEX.finditer(texte):
        sections.append((titre, texte[debut:trouve.start()]))
        mots = (trouve.group(1) or trouve.group(2)).strip().lower().split()
        titre = ' '.join(ACCENTS.get(mot, mot) for mot in mots).capitalize()
        debut = trouve.end()
    sections.append((titre, texte[debut:]))

    resultat = []
    for titre, morceau in sections:
        elements = [element.strip(' ;,.') for element in PUCE_REGEX.split(' ' + morceau) if element.strip(' ;,.')]
        if not elements:
            continue
        if len(elements) > 1:
            resultat.append({'titre': titre, 'puces': elements, 'paragraphes': []})
        else:
            resultat.append({'titre': titre, 'puces': [], 'paragraphes': paragraphes(elements[0])})
    return resultat


def maniere_de_postuler(offre):
    """'lien' (site de l'employeur), 'email' (adresse trouvee dans l'annonce), 'close' ou 'rien'."""
    if est_close(offre):
        return 'close'
    lien = offre.lien_candidature or ''
    if lien.startswith('mailto:'):
        return 'email'
    return 'lien' if lien else 'rien'
