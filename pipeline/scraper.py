"""Etape 3 : recupere les offres d'emploi de mediacongo.net.

Courtoisie web :
- le robots.txt du site demande 10 secondes entre deux requetes (Crawl-delay) : on les respecte ;
- le robot s'identifie clairement (User-Agent) ;
- il tourne a part du site CVBoost, jamais pendant la visite d'un utilisateur.

Lancement : python -m pipeline.scraper [nombre_de_pages]   (30 offres par page, 5 pages par defaut)
Les offres deja presentes dans data/offres_brutes.csv ne sont pas telechargees une seconde fois.
"""
import io
import re
import sys
import time
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from .config import OFFRES_BRUTES

BASE_URL = 'https://www.mediacongo.net/'
LISTE_URL = BASE_URL + 'emplois-search--tri-offres_recentes-page-{}.html'
USER_AGENT = 'CVBoostBot/1.0 (projet etudiant Kadea Academy)'
DELAI = 10            # secondes entre deux requetes (Crawl-delay du robots.txt)
TIMEOUT = 20          # secondes maximum pour une reponse
PDF_MAX = 5 * 1024 * 1024
TEXTE_MIN = 300       # en dessous, la description n'est pas exploitable par l'IA

# Couleur de la ligne dans la liste du site -> statut de l'offre
STATUTS = {'clas1': 'en_cours', 'clas2': 'moins_de_3_jours', 'clas3': 'expiree', 'clas4': 'non_precise'}
# Le site n'a pas de champ salaire : on cherche "salaire ... 800 USD" dans le texte de l'annonce
SALAIRE_REGEX = re.compile(r'(?:salaire|r[ée]mun[ée]ration)[^\n]{0,80}?\d[\d .,]*\s*(?:\$|usd|dollars?|fc|cdf)',
                           re.IGNORECASE)

session = requests.Session()
session.headers['User-Agent'] = USER_AGENT


def telecharger(url):
    """Attend DELAI secondes puis telecharge la page. Renvoie la reponse, ou None en cas d'erreur."""
    time.sleep(DELAI)
    try:
        reponse = session.get(url, timeout=TIMEOUT)
        reponse.raise_for_status()
        return reponse
    except requests.RequestException as erreur:
        print(f'  erreur sur {url} : {erreur}')
        return None


def texte_propre(element):
    return re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', element.get_text('\n'))).strip()


def lire_liste(html):
    """Extrait les offres d'une page de liste : titre, entreprise, lieu, date, lien, statut."""
    offres = []
    for case in BeautifulSoup(html, 'html.parser').select('table.table_datas td.tdclas'):
        colonnes = case.find_parent('tr').find_all('td')
        statut = next((STATUTS[c] for c in case['class'] if c in STATUTS), 'non_precise')
        offres.append({
            'titre': colonnes[1].find('strong').get_text(strip=True),
            'entreprise': colonnes[2].get_text(strip=True),
            'lieu': colonnes[3].get_text(strip=True),
            'date_publication': colonnes[4].get_text(strip=True),
            'url': urljoin(BASE_URL, colonnes[1].find('a')['href']),
            'statut': statut,
        })
    return offres


def texte_du_pdf(url):
    """Certaines annonces sont un PDF : on en extrait le texte avec pypdf."""
    reponse = telecharger(url)
    if reponse is None or len(reponse.content) > PDF_MAX:
        return ''
    try:
        return '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(reponse.content)).pages).strip()
    except Exception as erreur:  # PDF abime ou protege
        print(f'  PDF illisible {url} : {erreur}')
        return ''


def lire_offre(html):
    """Extrait la description d'une offre. Selon l'annonce, elle est en texte, dans un PDF ou en image."""
    bloc = BeautifulSoup(html, 'html.parser').find('div', class_='more_hemploi_left')
    titres = bloc.find_all('div', class_='emploi_section') if bloc else []
    section = next((t for t in titres if t.get_text(strip=True) == 'Description'), None)
    contenu = section.find_next_sibling('div', class_='article_ttext') if section else None
    if contenu is None:
        return {'description': None, 'source_description': 'vide', 'lien_candidature': None, 'salaire': None}

    liens = [a['href'] for a in contenu.find_all('a', href=True)]
    lien_externe = next((l for l in liens if l.startswith('http') and 'mediacongo' not in l), None)
    texte, source = texte_propre(contenu), 'texte'
    if len(texte) < TEXTE_MIN:
        pdf = next((l for l in liens if l.lower().endswith('.pdf') and 'mediacongo' in l), None)
        texte_pdf = texte_du_pdf(pdf) if pdf else ''
        if len(texte_pdf) >= TEXTE_MIN:
            texte, source = texte_pdf, 'pdf'
        else:
            # Annonce scannee en image : pas de texte exploitable (une lecture OCR serait necessaire)
            texte, source = None, 'image' if contenu.find('img') else 'vide'

    salaire = SALAIRE_REGEX.search(texte) if texte else None
    return {'description': texte, 'source_description': source,
            'lien_candidature': lien_externe, 'salaire': salaire.group(0) if salaire else None}


def charger_existantes():
    try:
        return pd.read_csv(OFFRES_BRUTES)
    except FileNotFoundError:
        return pd.DataFrame()


def main(nombre_pages=5):
    existantes = charger_existantes()
    deja_vues = set(existantes['url']) if 'url' in existantes else set()
    nouvelles = []
    debut = time.time()

    for numero in range(1, nombre_pages + 1):
        reponse = telecharger(LISTE_URL.format(numero))
        if reponse is None:
            break
        offres = [o for o in lire_liste(reponse.text) if o['url'] not in deja_vues]
        print(f'Page {numero} : {len(offres)} nouvelle(s) offre(s)')
        for offre in offres:
            page = telecharger(offre['url'])
            if page is None:
                continue
            offre.update(lire_offre(page.text))
            nouvelles.append(offre)
            deja_vues.add(offre['url'])
            print(f"  [{offre['source_description']:5}] {offre['titre'][:70]}")
        # Sauvegarde apres chaque page : un arret en cours de route ne perd rien
        pd.concat([existantes, pd.DataFrame(nouvelles)], ignore_index=True).to_csv(OFFRES_BRUTES, index=False)

    print(f'{len(nouvelles)} offre(s) ajoutee(s) en {(time.time() - debut) / 60:.1f} min -> {OFFRES_BRUTES}')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
