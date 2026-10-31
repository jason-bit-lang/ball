"""Parcours d'un nouvel utilisateur sur le site lance en local (sans cle OpenAI)."""
import io, re, sys, time, zipfile, requests
SITE = 'http://127.0.0.1:5000'
# Attendre que le site et l'API repondent (premier lancement : creation de la base)
debut = time.time()
for essai in range(120):
    try:
        requests.get(SITE + '/health', timeout=2); requests.get('http://127.0.0.1:8000/health', timeout=2); break
    except requests.RequestException:
        time.sleep(1)
print(f'demarrage du site et de l API : {time.time() - debut:.1f} s')
s = requests.Session()
resultats = []
def verifier(nom, condition, detail=''):
    resultats.append(condition)
    print(('  OK    ' if condition else '  ECHEC ') + nom + ('' if condition else '  ' + str(detail)[:200]))
def jeton(page):
    return re.search(r'name="csrf-token" content="([^"]+)"', page).group(1)
try:
    sante = s.get(SITE + '/health', timeout=10).json()
    verifier('/health site + base + api', sante == {'site': 'ok', 'base': 'ok', 'api': 'ok'}, sante)
    accueil = s.get(SITE + '/')
    verifier('accueil', accueil.ok and 'prend vie ici' in accueil.text, accueil.status_code)
    for page in ['/static/style.css', '/static/site.js', '/static/envoi.js', '/static/entretien.js', '/login']:
        r = s.get(SITE + page); verifier('page ' + page, r.ok, r.status_code)
    r = s.post(SITE + '/register', data={'csrf_token': jeton(s.get(SITE + '/register').text), 'nom': 'Mbuyi',
               'prenom': 'Grace', 'email': 'grace@test.cd', 'password': 'MotDePasse2026',
               'confirmation_mot_secret': 'MotDePasse2026'})
    verifier('inscription -> Propulser votre CV', r.url.endswith('/upload'), r.url)
    lignes = ['Grace Mbuyi', 'Comptable - Kinshasa - grace.mbuyi@test.cd - +243 81 000 0000', 'Experience professionnelle',
              'Comptable chez Rawbank (2019 - 2025) : comptabilite generale, fiscalite, tresorerie, clotures annuelles.',
              'Formation', 'Licence en sciences comptables, Universite de Kinshasa (2018)',
              'Competences', 'Comptabilite OHADA, Excel avance, SAGE, audit, gestion budgetaire', 'Langues', 'Francais, anglais, lingala']
    paragraphes = ''.join('<w:p><w:r><w:t>' + l + '</w:t></w:r></w:p>' for l in lignes)
    fichier = io.BytesIO()
    with zipfile.ZipFile(fichier, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                         'wordprocessingml/2006/main"><w:body>' + paragraphes + '</w:body></w:document>')
    debut = time.time()
    r = s.post(SITE + '/upload', data={'csrf_token': jeton(r.text)}, files={'cv': ('mon cv.docx', fichier.getvalue())},
               headers={'X-Requested-With': 'fetch'})
    verifier(f'envoi du CV ({time.time() - debut:.1f} s)', r.ok and 'adresse' in r.json(), r.text)
    resultats_page = s.get(SITE + r.json()['adresse'])
    nb = resultats_page.text.count('carte-offre')
    verifier(f'page des opportunites ({nb} offres)', nb > 0, resultats_page.status_code)
    lien = re.search(r'href="(/offre/[^"]+)"', resultats_page.text)
    verifier('page d\'une offre', lien is not None and s.get(SITE + lien.group(1)).ok)
    verifier('historique', s.get(SITE + '/history').ok)
    s.get(SITE + '/logout')
    r = s.post(SITE + '/login', data={'csrf_token': jeton(s.get(SITE + '/login').text), 'email': 'grace@test.cd',
               'password': 'MotDePasse2026'})
    verifier('reconnexion -> historique', r.url.endswith('/history'), r.url)
    sante_api = requests.get('http://127.0.0.1:8000/health', timeout=10)
    verifier('API du pitch /health', sante_api.ok, sante_api.text)
except Exception as erreur:
    verifier('parcours sans exception', False, repr(erreur))
print(f'bilan: {sum(resultats)}/{len(resultats)}')
sys.exit(0 if all(resultats) else 1)
