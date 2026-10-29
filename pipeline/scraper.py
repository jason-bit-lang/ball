"""Etape 3 : recupere les offres d'emploi de mediacongo.net.

Courtoisie web :
- le robots.txt du site demande 10 secondes entre deux requetes (Crawl-delay) : on les respecte ;
- le robot s'identifie clairement (User-Agent) ;
- il tourne a part du site CVBoost, jamais pendant la visite d'un utilisateur.

Lancement : python -m pipeline.scraper [nombre_de_pages]   (30 offres par page, 5 pages par defaut)
Les offres deja presentes dans data/offres_brutes.csv ne sont pas telechargees une seconde fois,
sauf les annonces en image, relues par OCR si Tesseract est installe.

Annonces scannees (OCR) : il faut installer Tesseract avec le francais.
  Windows : https://github.com/UB-Mannheim/tesseract/wiki (cocher "French" a l'installation)
  Linux   : sudo apt install tesseract-ocr tesseract-ocr-fra
Sans Tesseract, le scraper fonctionne quand meme et marque ces annonces "image".
"""
import io
import re
import sys
import time
from urllib.parse import urljoin
import pandas as pd
import pytesseract
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pypdf import PdfReader
from .config import OFFRES_BRUTES

BASE_URL = 'https://www.mediacongo.net/'
LISTE_URL = BASE_URL + 'emplois-search--tri-offres_recentes-page-{}.html'
USER_AGENT = 'CVBoostBot/1.0 (projet etudiant Kadea Academy)'
DELAI = 10            # secondes entre deux requetes (Crawl-delay du robots.txt)
TIMEOUT = 20          # secondes maximum pour une reponse
FICHIER_MAX = 5 * 1024 * 1024   # PDF ou image : 5 Mo maximum
IMAGES_MAX = 6        # une annonce scannee fait rarement plus de 6 pages
TEXTE_MIN = 300       # en dessous, la description n'est pas exploitable par l'IA

# Couleur de la ligne dans la liste du site -> statut de l'offre
STATUTS = {'clas1': 'en_cours', 'clas2': 'moins_de_3_jours', 'clas3': 'expiree', 'clas4': 'non_precise'}
# Le site n'a pas de champ salaire : on cherche "salaire ... 800 USD" dans le texte de l'annonce
SALAIRE_REGEX = re.compile(r'(?:salaire|r[ée]mun[ée]ration)[^\n]{0,80}?\d[\d .,]*\s*(?:\$|usd|dollars?|fc|cdf)',
                           re.IGNORECASE)

# Une session garde la meme connexion d'une requete a l'autre (plus rapide, et plus leger pour le site visite)
session = requests.Session()
session.headers['User-Agent'] = USER_AGENT


def telecharger(url):
    """Attend DELAI secondes puis telecharge la page. Renvoie la reponse, ou None en cas d'erreur.
    Toutes les requetes passent par ici : le delai de courtoisie ne peut jamais etre oublie."""
    time.sleep(DELAI)
    try:
        reponse = session.get(url, timeout=TIMEOUT)
        reponse.raise_for_status()  # code d'erreur (404, 500...) -> exception, attrapee juste en dessous
        return reponse
    except requests.RequestException as erreur:
        print(f'  erreur sur {url} : {erreur}')
        return None


def texte_propre(element):
    """Texte d'un bloc HTML sans lignes vides en trop ni espaces en double."""
    return re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', element.get_text('\n'))).strip()


def lire_liste(html):
    """Extrait les offres d'une page de liste : titre, entreprise, lieu, date, lien, statut."""
    offres = []
    # Chaque offre est une ligne du tableau "table_datas" ; la case "tdclas" porte la couleur du statut
    for case in BeautifulSoup(html, 'html.parser').select('table.table_datas td.tdclas'):
        colonnes = case.find_parent('tr').find_all('td')  # les cases de la ligne : titre, entreprise, lieu, date
        # Premiere classe connue de la case (clas1, clas2...), sinon 'non_precise'
        statut = next((STATUTS[c] for c in case['class'] if c in STATUTS), 'non_precise')
        offres.append({
            'titre': colonnes[1].find('strong').get_text(strip=True),
            'entreprise': colonnes[2].get_text(strip=True),
            'lieu': colonnes[3].get_text(strip=True),
            'date_publication': colonnes[4].get_text(strip=True),
            'url': urljoin(BASE_URL, colonnes[1].find('a')['href']),  # lien relatif -> adresse complete
            'statut': statut,
        })
    return offres


def lire_pdf(contenu):
    """Texte de toutes les pages d'un PDF joint a l'annonce."""
    return '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(contenu)).pages)


def lire_image(contenu):
    """OCR : Tesseract lit le texte de l'image (annonces en francais ou en anglais)."""
    return pytesseract.image_to_string(Image.open(io.BytesIO(contenu)), lang='fra+eng')


def texte_du_fichier(url, lire):
    """Telecharge un PDF ou une image puis en extrait le texte avec la fonction `lire`."""
    reponse = telecharger(url)
    if reponse is None or len(reponse.content) > FICHIER_MAX:  # fichier trop gros : on ne le lit pas
        return ''
    try:
        return lire(reponse.content).strip()
    except Exception as erreur:  # fichier abime, protege ou format inconnu
        print(f'  fichier illisible {url} : {erreur}')
        return ''


def ocr_disponible():
    """Vrai si le logiciel Tesseract est installe (pytesseract n'est qu'un intermediaire vers lui)."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except pytesseract.TesseractNotFoundError:
        return False


OCR_ACTIF = ocr_disponible()  # verifie une seule fois, au lancement du scraper


def lire_offre(html):
    """Extrait la description d'une offre. Selon l'annonce, elle est en texte, dans un PDF ou en image."""
    # La description est le bloc qui suit le titre "Description" dans la colonne de gauche de la page
    bloc = BeautifulSoup(html, 'html.parser').find('div', class_='more_hemploi_left')
    titres = bloc.find_all('div', class_='emploi_section') if bloc else []
    section = next((t for t in titres if t.get_text(strip=True) == 'Description'), None)
    contenu = section.find_next_sibling('div', class_='article_ttext') if section else None
    if contenu is None:
        return {'description': None, 'source_description': 'vide', 'lien_candidature': None, 'salaire': None}

    liens = [a['href'] for a in contenu.find_all('a', href=True)]
    # Lien de candidature : le premier lien vers un autre site que mediacongo (site de l'employeur)
    lien_externe = next((l for l in liens if l.startswith('http') and 'mediacongo' not in l), None)
    images = [urljoin(BASE_URL, img['src']) for img in contenu.find_all('img', src=True)][:IMAGES_MAX]

    # On essaie dans l'ordre : le texte de la page, puis le PDF joint, puis l'OCR des images
    texte, source = texte_propre(contenu), 'texte'
    if len(texte) < TEXTE_MIN:
        pdf = next((l for l in liens if l.lower().endswith('.pdf') and 'mediacongo' in l), None)
        texte, source = (texte_du_fichier(pdf, lire_pdf) if pdf else ''), 'pdf'
    if len(texte) < TEXTE_MIN and images and OCR_ACTIF:
        texte, source = '\n'.join(texte_du_fichier(url, lire_image) for url in images), 'ocr'
    if len(texte) < TEXTE_MIN:
        # Rien de lisible : annonce en image sans OCR, ou annonce vide
        texte, source = None, 'image' if images else 'vide'

    salaire = SALAIRE_REGEX.search(texte) if texte else None
    return {'description': texte, 'source_description': source,
            'lien_candidature': lien_externe, 'salaire': salaire.group(0) if salaire else None}


def charger_existantes():
    """Offres deja recuperees lors des lancements precedents (tableau vide la premiere fois)."""
    try:
        return pd.read_csv(OFFRES_BRUTES, dtype=str)  # tout en texte : on peut remplacer n'importe quelle case
    except FileNotFoundError:
        return pd.DataFrame()


def relire_images(existantes):
    """Relit par OCR les annonces enregistrees en image (par exemple avant l'installation de Tesseract)."""
    a_relire = existantes.index[existantes['source_description'] == 'image'] if len(existantes) else []
    if len(a_relire) == 0:
        return
    if not OCR_ACTIF:
        print(f'{len(a_relire)} annonce(s) en image non lue(s) : installez Tesseract pour activer l\'OCR.')
        return
    print(f'{len(a_relire)} annonce(s) en image a relire par OCR')
    for i in a_relire:
        page = telecharger(existantes.at[i, 'url'])
        if page is None:
            continue
        for cle, valeur in lire_offre(page.text).items():
            existantes.at[i, cle] = valeur
        print(f"  [{existantes.at[i, 'source_description']:5}] {existantes.at[i, 'titre'][:70]}")
        existantes.to_csv(OFFRES_BRUTES, index=False)  # sauvegarde au fur et a mesure


def main(nombre_pages=5):
    """Parcourt les pages de la liste des offres, puis chaque nouvelle offre."""
    existantes = charger_existantes()
    relire_images(existantes)
    # Adresses deja connues : ces offres ne sont pas telechargees une seconde fois
    deja_vues = set(existantes['url']) if 'url' in existantes else set()
    nouvelles = []
    debut = time.time()

    for numero in range(1, nombre_pages + 1):
        reponse = telecharger(LISTE_URL.format(numero))
        if reponse is None:
            break  # site injoignable : inutile d'essayer les pages suivantes
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


# "python -m pipeline.scraper 3" : sys.argv[1] vaut "3" (nombre de pages) ; 5 pages si rien n'est precise
if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
