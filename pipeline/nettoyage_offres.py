"""Etape 4 : nettoie les offres scrapees pour les rendre utilisables par l'IA ("IA-Ready").

Entree  : data/offres_brutes.csv  (cree par pipeline/scraper.py)
Sortie  : data/offres_propres.csv
Lancement : python -m pipeline.nettoyage_offres

Pourquoi nettoyer ? Les offres scrapees contiennent des doublons, des cases vides, des salaires ecrits
de mille facons et des textes abimes par l'OCR. Une IA entrainee ou interrogee sur ces donnees
donnerait de mauvais resultats : "garbage in, garbage out".
"""
import re
import unicodedata
from datetime import date
import pandas as pd
from .config import OFFRES_BRUTES, OFFRES_PROPRES, TAUX_CDF_USD

# Colonnes attendues dans le fichier brut (celles qui manquent sont creees vides)
COLONNES = ['titre', 'entreprise', 'lieu', 'description', 'salaire', 'date_publication', 'url',
            'statut', 'source_description', 'lien_candidature']

# Competences recherchees dans le titre et la description (ecrites sans accents, en minuscules,
# en francais et en anglais car beaucoup d'annonces sont en anglais).
# Cle = nom de la colonne creee, valeur = mots qui signalent cette competence.
# Les mots trop generaux sont evites : "recrutement", "formation", "conduite" (code de conduite),
# "site web" (postulez sur notre site web), "droit", "budget"... apparaissent dans presque toutes
# les annonces et donneraient de fausses competences.
COMPETENCES = {
    'python': ['python', 'django', 'flask'],
    'javascript': ['javascript', 'react', 'node.js', 'nodejs', 'vue.js', 'angular'],
    'php': ['php', 'laravel', 'symfony'],
    'java': ['java', 'spring boot'],
    'web': ['html', 'css', 'developpeur web', 'web developer', 'full stack', 'fullstack', 'wordpress'],
    'sql': ['sql', 'mysql', 'postgresql', 'base de donnees', 'bases de donnees', 'database'],
    'reseaux': ['administrateur reseau', 'reseaux informatiques', 'network administrator', 'cisco', 'linux',
                'windows server'],
    'donnees': ['analyse de donnees', 'data analysis', 'data officer', 'data manager', 'power bi', 'stata',
                'spss', 'dhis2', 'kobo', 'odk'],
    'bureautique': ['excel', 'powerpoint', 'microsoft office', 'ms office', 'pack office', 'bureautique'],
    'comptabilite': ['comptable', 'comptabilite', 'accountant', 'accounting', 'sage', 'ohada', 'fiscalite',
                     'tresorerie'],
    'finance': ['finance', 'financier', 'financiere', 'financial', 'audit', 'controle de gestion', 'grants'],
    'gestion_projet': ['gestion de projet', 'gestion des projets', 'chef de projet', 'project manager',
                       'project management', 'coordonnateur', 'coordinateur', 'coordinator'],
    'suivi_evaluation': ['suivi et evaluation', 'suivi-evaluation', 'suivi evaluation',
                         'monitoring and evaluation', 'm&e', 'meal'],
    'rh': ['ressources humaines', 'human resources', 'paie', 'payroll', 'gestion du personnel'],
    'logistique': ['logistique', 'logistics', 'approvisionnement', 'procurement', 'supply chain',
                   'gestion de stock', 'magasinier', 'passation des marches'],
    'commercial': ['commercial', 'commerciale', 'business development', 'prospection', 'sales'],
    'marketing': ['marketing', 'community manager', 'communication digitale', 'charge de communication',
                  'communication officer'],
    'juridique': ['juriste', 'juridique', 'avocat', 'lawyer', 'legal officer'],
    'sante': ['medecin', 'infirmier', 'infirmiere', 'nurse', 'pharmacien', 'sante publique', 'public health',
              'nutrition', 'epidemiologie'],
    'enseignement': ['enseignant', 'professeur', 'formateur', 'teacher', 'renforcement des capacites'],
    'ingenierie': ['ingenieur', 'engineer', 'genie civil', 'electricien', 'electrician', 'mecanicien',
                   'mechanic', 'btp'],
    'environnement': ['environnemental', 'environnementale', 'environnementaux', 'environmental',
                      'changement climatique', 'climate change'],
    'agriculture': ['agriculture', 'agricole', 'agricultural', 'agronome', 'agronomie', 'elevage'],
    'qualite_laboratoire': ['assurance qualite', 'quality assurance', 'laboratoire', 'laboratory', 'smq'],
    'securite': ['agent de securite', 'security officer', 'gardiennage', 'surete'],
    'chauffeur': ['chauffeur', 'driver', 'permis de conduire'],
    'anglais': ['anglais', 'english', 'bilingue'],
    'langues_locales': ['swahili', 'lingala', 'tshiluba', 'kikongo'],
}


def normaliser(texte):
    """Minuscules, sans accents, espaces multiples reduits : 'Développeur  Web' -> 'developpeur web'."""
    # NFKD separe chaque lettre de son accent ("e" + accent) ; encode('ascii', 'ignore') jette les accents
    texte = unicodedata.normalize('NFKD', str(texte)).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', texte).strip().lower()


# Une expression reguliere par competence, compilee une seule fois.
# (?<!\w) et (?!\w) evitent de trouver "java" dans "javascript" ou "data" dans "database".
COMPETENCES_REGEX = {
    nom: re.compile('|'.join(rf'(?<!\w){re.escape(mot)}(?!\w)' for mot in mots))
    for nom, mots in COMPETENCES.items()
}


def convertir_salaire(texte):
    """Renvoie (minimum, maximum) en dollars, ou (None, None) si le salaire n'est pas chiffre.

    Exemples : '800 USD' -> (800, 800) ; '1.500.000 FC' -> (535.7, 535.7) ;
    '$500 - $700' -> (500, 700) ; 'A negocier' -> (None, None)
    """
    if pd.isna(texte):
        return None, None
    texte = normaliser(texte)
    # Les espaces, points et virgules entre chiffres sont des separateurs de milliers
    nombres = [float(re.sub(r'[ .,]', '', n)) for n in re.findall(r'\d+(?:[ .,]\d{3})*', texte)]
    nombres = [n for n in nombres if n >= 10]  # ignore les petits nombres ("3 ans", "2 postes")
    if not nombres:
        return None, None

    if '$' in texte or 'usd' in texte or 'dollar' in texte:
        taux = 1
    elif re.search(r'\b(fc|cdf|franc)', texte):
        taux = 1 / TAUX_CDF_USD
    else:
        # Monnaie non precisee : un montant enorme est forcement en francs congolais
        taux = 1 / TAUX_CDF_USD if max(nombres) > 20000 else 1
    return round(min(nombres) * taux, 1), round(max(nombres) * taux, 1)


# Annonces qui ne sont pas des offres : resultats d'un recrutement deja termine
RESULTATS_REGEX = re.compile(r'publication (?:provisoire |definitive )?des resultats|liste restreinte'
                             r'|intention d.?attribution|avis d.?attribution|attribution du marche'
                             r'|avis d.?infructuosite|declare infructueux')

# Qualite d'un texte (surtout utile pour l'OCR) : part des mots bien formes
MOT_REGEX = re.compile(r'[^\W\d_]{2,}|\d+')
QUALITE_MIN = 0.75


def est_annonce_de_resultats(titre, description):
    """Vrai si l'annonce publie les resultats d'un recrutement termine (personne ne peut plus y postuler)."""
    debut = normaliser(titre) + ' ' + normaliser(description)[:600]  # le sujet est annonce au debut
    return bool(RESULTATS_REGEX.search(debut))


def qualite_texte(texte):
    """Entre 0 et 1. Un texte mal lu par l'OCR contient beaucoup de melanges comme 'a9', 'Arr0s' ou '|=;'."""
    mots = [m.strip('.,;:!?()[]«»"\'’-') for m in str(texte).split()]  # mots sans la ponctuation autour
    mots = [m for m in mots if m]
    # Part des mots "propres" (que des lettres, ou que des chiffres) parmi tous les mots
    return sum(bool(MOT_REGEX.fullmatch(m)) for m in mots) / len(mots) if mots else 0


def competences_connues(noms):
    """Garde seulement les noms de competences connus, sans doublon : ['sante', 'luz', 'sante'] -> 'sante'."""
    gardees = []
    for nom in noms:
        nom = nom.strip()
        if nom in COMPETENCES and nom not in gardees:
            gardees.append(nom)
    return ', '.join(gardees)


# Date limite de candidature ecrite dans l'annonce : "au plus tard le 03 novembre 2026",
# "Date limite : 10/11/2026", "cloture de la publication : 16 novembre 2026"...
MOIS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre',
        'novembre', 'decembre']
DATE_LIMITE_REGEX = re.compile(r'(?:date limite|au plus tard|cloture|deadline|dernier delai|avant le)\b\D{0,50}?'
                               r'(\d{1,2})(?:er)?\s*[/.-]?\s*(' + '|'.join(MOIS) + r'|\d{1,2})\s*[/.-]?\s*(20\d\d)')
EMAIL_REGEX = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
SITE_REGEX = re.compile(r'(?:https?://|www\.)[\w-]+(?:\.[\w-]+)+(?:/\S*)?', re.I)


def trouver_date_limite(description):
    """Premiere date limite lisible dans l'annonce, au format AAAA-MM-JJ, sinon None."""
    # normaliser() retire les accents : "cloture", "fevrier"... s'ecrivent comme dans l'expression reguliere
    for jour, mois, annee in DATE_LIMITE_REGEX.findall(normaliser(description)):
        # Le mois est ecrit en lettres ("novembre") ou en chiffres ("11")
        numero_mois = MOIS.index(mois) + 1 if mois in MOIS else int(mois)
        try:
            return date(int(annee), numero_mois, int(jour)).isoformat()
        except ValueError:  # date impossible (32 octobre, mois 13...) : on essaie la suivante
            continue
    return None


def trouver_contact(description):
    """Quand l'annonce n'a pas de lien de candidature : une adresse email (mailto:) ou un site cite."""
    # L'email passe en premier : c'est le moyen de postuler le plus direct
    email = EMAIL_REGEX.search(description)
    if email:
        return 'mailto:' + email.group(0).rstrip('.')  # retire un point de fin de phrase colle a l'adresse
    site = SITE_REGEX.search(description)
    if site:
        adresse = site.group(0).rstrip('.,;)')
        return adresse if adresse.lower().startswith('http') else 'https://' + adresse  # "www.x.cd" -> lien cliquable
    return None


MENTIONS_MIN = 2  # une seule mention dans une longue annonce est souvent une formule standard


def trouver_competences(titre, description=''):
    """Une competence est retenue si elle est dans le titre, ou citee au moins MENTIONS_MIN fois
    dans la description."""
    titre, description = normaliser(titre), normaliser(description)
    return [nom for nom, regex in COMPETENCES_REGEX.items()
            if regex.search(titre) or len(regex.findall(description)) >= MENTIONS_MIN]


def nettoyer(df):
    """Applique toutes les etapes de nettoyage. Renvoie le tableau propre et un resume chiffre."""
    resume = {'offres_brutes': len(df)}
    df = df.reindex(columns=COLONNES).copy()  # garde nos colonnes, ajoute celles qui manquent

    # 1. Textes : espaces en trop retires, cellules vides transformees en valeurs manquantes
    for col in COLONNES:
        df[col] = df[col].astype('string').str.replace(r'\s+', ' ', regex=True).str.strip()
        df[col] = df[col].replace('', pd.NA)

    # 2. Sans titre ou sans description, une offre est inutilisable par l'IA
    avant = len(df)
    df = df.dropna(subset=['titre', 'description'])
    resume['sans_titre_ou_description'] = avant - len(df)
    df[['entreprise', 'lieu']] = df[['entreprise', 'lieu']].fillna('Non precise')

    # 2 bis. Resultats de recrutements termines (personne ne peut plus y postuler)
    resultats = [est_annonce_de_resultats(t, d) for t, d in zip(df['titre'], df['description'])]
    df = df[[not r for r in resultats]]
    resume['annonces_de_resultats'] = sum(resultats)

    # 2 ter. Textes trop abimes (annonce scannee floue mal lue par l'OCR)
    df['qualite_texte'] = df['description'].map(qualite_texte).round(2)
    avant = len(df)
    df = df[df['qualite_texte'] >= QUALITE_MIN]
    resume['texte_illisible'] = avant - len(df)

    # 3. Doublons : meme lien, ou meme titre + entreprise + description (sans tenir compte des accents)
    avant = len(df)
    # "~" veut dire "pas" : on garde les lignes qui ne sont PAS des doublons
    df = df[~(df['url'].notna() & df.duplicated(subset='url'))]
    cle = df['titre'].map(normaliser) + '|' + df['entreprise'].map(normaliser) + '|' + df['description'].map(normaliser)
    df = df[~cle.duplicated()]
    resume['doublons'] = avant - len(df)

    # 4. Salaires convertis en dollars (minimum, maximum, moyenne)
    salaires = df['salaire'].map(convertir_salaire)
    df['salaire_min_usd'] = salaires.map(lambda s: s[0]).astype('Float64')
    df['salaire_max_usd'] = salaires.map(lambda s: s[1]).astype('Float64')
    df['salaire_moyen_usd'] = ((df['salaire_min_usd'] + df['salaire_max_usd']) / 2).round(1)
    resume['salaires_chiffres'] = int(df['salaire_moyen_usd'].notna().sum())

    # 5. Dates au format AAAA-MM-JJ (jour en premier dans les dates congolaises : 26/10/2026).
    # format='mixed' accepte aussi les dates deja ecrites 2026-10-26 dans le meme fichier.
    df['date_publication'] = pd.to_datetime(df['date_publication'], dayfirst=True, errors='coerce',
                                            format='mixed').dt.date

    # 5 bis. Date limite de candidature et moyen de postuler, lus dans le texte de l'annonce
    df['date_limite'] = df['description'].map(trouver_date_limite)
    # Une date limite anterieure a la publication est une autre date de l'annonce : on l'ignore
    publication = df['date_publication'].astype('string')
    df.loc[df['date_limite'] < publication, 'date_limite'] = None
    resume['avec_date_limite'] = int(df['date_limite'].notna().sum())
    df['lien_candidature'] = df['lien_candidature'].fillna(df['description'].map(trouver_contact))
    resume['avec_moyen_de_postuler'] = int(df['lien_candidature'].notna().sum())

    # 6. Competences : une liste lisible + une colonne 0/1 par competence (encodage "one-hot")
    listes = pd.Series([trouver_competences(t, d) for t, d in zip(df['titre'], df['description'])],
                       index=df.index)
    df['competences'] = listes.map(', '.join)
    for nom in COMPETENCES:
        df[f'comp_{nom}'] = listes.map(lambda liste: int(nom in liste))
    resume['sans_competence_detectee'] = int((listes.map(len) == 0).sum())

    # 7. Texte unique donne a l'IA (matching TF-IDF et fine-tuning)
    df['texte_ia'] = (df['titre'] + '. ' + df['description']).map(normaliser)

    # Numerotation des offres propres de 1 a N, dans une colonne "id" placee en premier
    df = df.reset_index(drop=True)
    df.insert(0, 'id', df.index + 1)
    resume['offres_propres'] = len(df)
    return df, resume


def main():
    """Lit les offres brutes, les nettoie, enregistre le resultat et affiche le resume de chaque etape."""
    try:
        brutes = pd.read_csv(OFFRES_BRUTES)
    except FileNotFoundError:
        print(f'Fichier introuvable : {OFFRES_BRUTES}. Lancez d\'abord : python -m pipeline.scraper')
        return
    propres, resume = nettoyer(brutes)
    propres.to_csv(OFFRES_PROPRES, index=False)
    for etape, nombre in resume.items():
        print(f'{etape:28} {nombre}')
    print(f'Fichier cree : {OFFRES_PROPRES}')


if __name__ == '__main__':
    main()
