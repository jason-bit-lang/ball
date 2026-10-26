"""Etape 4 : nettoie les offres scrapees pour les rendre utilisables par l'IA ("IA-Ready").

Entree  : data/offres_brutes.csv  (colonnes : titre, entreprise, lieu, description, salaire,
          date_publication, url)
Sortie  : data/offres_propres.csv
Lancement : python -m pipeline.nettoyage_offres
"""
import re
import unicodedata
import pandas as pd
from .config import OFFRES_BRUTES, OFFRES_PROPRES, TAUX_CDF_USD

COLONNES = ['titre', 'entreprise', 'lieu', 'description', 'salaire', 'date_publication', 'url']

# Competences recherchees dans le titre et la description (ecrites sans accents, en minuscules).
# Cle = nom de la colonne creee, valeur = mots qui signalent cette competence.
COMPETENCES = {
    'python': ['python', 'django', 'flask'],
    'javascript': ['javascript', 'react', 'node.js', 'nodejs', 'vue.js', 'angular'],
    'php': ['php', 'laravel', 'symfony'],
    'java': ['java', 'spring'],
    'web': ['html', 'css', 'developpeur web', 'site web', 'wordpress'],
    'sql': ['sql', 'mysql', 'postgresql', 'base de donnees', 'bases de donnees'],
    'reseaux': ['reseau', 'reseaux', 'cisco', 'administrateur systeme', 'linux', 'windows server'],
    'donnees': ['analyse de donnees', 'data', 'statistique', 'statistiques', 'power bi', 'stata', 'spss'],
    'bureautique': ['excel', 'word', 'powerpoint', 'microsoft office', 'pack office', 'bureautique'],
    'comptabilite': ['comptable', 'comptabilite', 'sage', 'ohada', 'fiscalite', 'tresorerie'],
    'finance': ['finance', 'financier', 'financiere', 'budget', 'audit', 'controle de gestion'],
    'gestion_projet': ['gestion de projet', 'chef de projet', 'coordination', 'coordinateur', 'coordonnateur'],
    'suivi_evaluation': ['suivi et evaluation', 'suivi-evaluation', 'suivi evaluation', 'monitoring', 'meal'],
    'rh': ['ressources humaines', 'recrutement', 'paie', 'gestion du personnel'],
    'logistique': ['logistique', 'approvisionnement', 'achats', 'supply chain', 'gestion de stock', 'magasinier'],
    'commercial': ['commercial', 'commerciale', 'vente', 'ventes', 'business development', 'prospection'],
    'marketing': ['marketing', 'communication', 'reseaux sociaux', 'community manager'],
    'juridique': ['juriste', 'juridique', 'droit', 'avocat', 'conformite'],
    'sante': ['medecin', 'infirmier', 'infirmiere', 'sante', 'pharmacien', 'nutrition'],
    'enseignement': ['enseignant', 'professeur', 'formateur', 'formation', 'education'],
    'ingenierie': ['ingenieur', 'genie civil', 'electricite', 'electricien', 'mecanique', 'btp'],
    'securite': ['securite', 'surete', 'gardiennage'],
    'chauffeur': ['chauffeur', 'permis de conduire', 'conduite'],
    'anglais': ['anglais', 'english', 'bilingue'],
    'langues_locales': ['swahili', 'lingala', 'tshiluba', 'kikongo'],
}


def normaliser(texte):
    """Minuscules, sans accents, espaces multiples reduits : 'Développeur  Web' -> 'developpeur web'."""
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


def trouver_competences(texte):
    texte = normaliser(texte)
    return [nom for nom, regex in COMPETENCES_REGEX.items() if regex.search(texte)]


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

    # 3. Doublons : meme lien, ou meme titre + entreprise + description (sans tenir compte des accents)
    avant = len(df)
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

    # 6. Competences : une liste lisible + une colonne 0/1 par competence (encodage "one-hot")
    listes = (df['titre'] + ' ' + df['description']).map(trouver_competences)
    df['competences'] = listes.map(', '.join)
    for nom in COMPETENCES:
        df[f'comp_{nom}'] = listes.map(lambda liste: int(nom in liste))
    resume['sans_competence_detectee'] = int((listes.map(len) == 0).sum())

    # 7. Texte unique donne a l'IA (matching TF-IDF et fine-tuning)
    df['texte_ia'] = (df['titre'] + '. ' + df['description']).map(normaliser)

    df = df.reset_index(drop=True)
    df.insert(0, 'id', df.index + 1)
    resume['offres_propres'] = len(df)
    return df, resume


def main():
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
