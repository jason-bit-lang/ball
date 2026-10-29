"""API du pitch vocal de CVBoost (FastAPI).

Le site Flask l'appelle (route /pitch/<id> dans app/routes.py). Elle n'est pas ouverte au public :
elle ecoute seulement sur la machine (127.0.0.1), ou dans le reseau prive de docker-compose.
Pourquoi ? Chaque pitch coute un appel a OpenAI : seul le site, qui verifie que le CV appartient bien
a l'utilisateur connecte, peut la declencher.

POST /speak-smart  {"document_id": 3}
  1. lit le texte du CV dans la base de donnees ;
  2. gpt-4o-mini le transforme en pitch oral d'environ 60 mots (reponse a "Presentez-vous") ;
  3. la voix Denise (edge-tts, gratuit, environ 1,5 s) le lit et l'enregistre en mp3 ;
  4. le fichier mp3 est envoye, puis supprime (BackgroundTasks).
GET /health : l'API repond.

Lancement en local, depuis la racine du projet : uvicorn api.main:app --port 8000
"""
import logging
import os
import tempfile
import time
from urllib.parse import quote
import edge_tts
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from config import ADRESSE_BASE  # config.py charge aussi le fichier .env (cle OpenAI)

MODELE_TEXTE = 'gpt-4o-mini'
VOIX = 'fr-FR-DeniseNeural'  # voix feminine francaise d'edge-tts, choisie par l'apprenant apres ecoute
DELAI_TEXTE = 6              # secondes au plus pour ecrire le pitch (environ 1,5 s)
DELAI_VOIX = 3               # secondes d'attente au plus pour la voix (le site doit repondre en moins de 10 s)
CV_MAX = 6000                # caracteres du CV envoyes a OpenAI (un CV plus long est coupe : cout et delai limites)

# Consignes reprises du module 3 (coach professionnel), ramenees a environ 60 mots.
# Un texte court se lit en 20 a 30 secondes : c'est la duree d'une bonne reponse a "Presentez-vous".
CONSIGNES = """Tu es un coach professionnel.
Tache : transforme le texte du CV fourni en un pitch oral captivant, a la premiere personne, qui repond
a la question d'entretien "Presentez-vous".
Contraintes :
- Redige un texte continu, sans puces, sans titres ni symboles speciaux.
- Utilise des phrases courtes et fluides, faciles a lire a voix haute.
- Entre 50 et 60 mots, en 4 ou 5 phrases courtes.
- N'invente rien : utilise seulement ce qui figure dans le CV.
- Reponds en francais."""

# Les erreurs sont ecrites dans la console : Render les affiche dans l'onglet "Logs"
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')
journal = logging.getLogger('api.pitch')
# Connexion a la meme base que le site. L'API n'importe pas le site Flask : elle reste legere en memoire.
moteur = create_engine(ADRESSE_BASE, pool_pre_ping=True)
app = FastAPI(title='CVBoost - pitch vocal')


class Demande(BaseModel):
    """Contenu attendu de la demande. Pydantic verifie que document_id est bien un nombre entier,
    sinon FastAPI repond tout seul une erreur 422."""
    document_id: int


def texte_du_cv(document_id):
    """Texte du CV enregistre a l'envoi (table document), ou None si le CV n'existe pas."""
    with moteur.connect() as connexion:
        # ":id" est un parametre : la valeur est envoyee a part, ce qui empeche toute injection SQL
        ligne = connexion.execute(text('SELECT texte FROM document WHERE id = :id'), {'id': document_id}).first()
    return ligne[0] if ligne else None


def ecrire_pitch(client, texte_cv):
    """Etape 2 : le CV brut devient un discours fluide."""
    # max_tokens=200 : de la marge pour 60 mots, mais pas de quoi ecrire un long texte (cout et delai)
    reponse = client.chat.completions.create(model=MODELE_TEXTE, max_tokens=200, messages=[
        {'role': 'system', 'content': CONSIGNES},
        {'role': 'user', 'content': texte_cv[:CV_MAX]}])
    return reponse.choices[0].message.content.strip()


def creer_voix(pitch, chemin):
    """Etape 3 : la voix Denise lit le pitch et l'enregistre dans le fichier mp3.
    Les deux delais evitent d'attendre indefiniment si le service de la voix ne repond pas."""
    edge_tts.Communicate(pitch, VOIX, connect_timeout=DELAI_VOIX, receive_timeout=DELAI_VOIX).save_sync(chemin)


@app.post('/speak-smart')
def speak_smart(demande: Demande, taches: BackgroundTasks):
    """Les quatre etapes du pitch (voir en haut du fichier). En cas d'erreur, le site recoit un code
    404 ou 503 et affiche un message clair a l'utilisateur."""
    debut = time.time()
    # Etape 1 : le texte du CV, lu une seule fois a l'envoi et garde dans la base
    texte_cv = texte_du_cv(demande.document_id)
    if not texte_cv:
        raise HTTPException(404, 'CV introuvable.')
    # Etape 2 : le pitch ecrit par gpt-4o-mini
    try:
        client = OpenAI(timeout=DELAI_TEXTE, max_retries=0)  # la cle vient de OPENAI_API_KEY
        pitch = ecrire_pitch(client, texte_cv)
    except Exception as erreur:  # cle absente, credit epuise, OpenAI trop lent...
        journal.error('Pitch non ecrit (%s)', type(erreur).__name__)
        raise HTTPException(503, "Le pitch n'a pas pu être préparé.")

    # Etape 3 : la voix, dans un fichier temporaire (mkstemp lui donne un nom unique)
    descripteur, chemin = tempfile.mkstemp(suffix='.mp3')
    os.close(descripteur)  # on ferme ce fichier vide : edge-tts va l'ouvrir et l'ecrire lui-meme
    try:
        creer_voix(pitch, chemin)
    except Exception as erreur:  # service de la voix injoignable ou trop lent
        os.remove(chemin)
        journal.error('Voix non creee (%s)', type(erreur).__name__)
        raise HTTPException(503, "La voix du pitch n'a pas pu être créée.")
    # Etape 4 : le fichier est supprime APRES l'envoi (BackgroundTasks), sinon il disparaitrait trop tot
    taches.add_task(os.remove, chemin)
    journal.info('Pitch du CV %s : %s mots, %.1f s', demande.document_id, len(pitch.split()), time.time() - debut)
    # Le texte du pitch accompagne le son dans un en-tete HTTP (accents encodes avec quote)
    return FileResponse(chemin, media_type='audio/mpeg', headers={'X-Pitch-Texte': quote(pitch)})


@app.get('/health')
def health():
    """Route de sante : le site l'appelle (dans sa propre route /health) pour savoir si l'API repond."""
    return {'statut': 'ok'}
