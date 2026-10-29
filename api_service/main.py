"""API du pitch vocal de CVBoost (FastAPI) : l'orchestrateur qui enchaine les deux services.

Le site Flask l'appelle (route /pitch/<id> dans app_web/routes.py). Elle n'est pas ouverte au public :
elle ecoute seulement sur la machine (127.0.0.1), ou dans le reseau prive de docker-compose.
Pourquoi ? Chaque pitch coute un appel a OpenAI : seul le site, qui verifie que le CV appartient bien
a l'utilisateur connecte, peut la declencher.

POST /speak-smart  {"document_id": 3}
  1. lit le texte du CV dans la base de donnees ;
  2. services/llm_reformulator.py : gpt-4o-mini en fait un pitch oral d'environ 60 mots ("Presentez-vous") ;
  3. services/tts_engine.py : la voix Denise (edge-tts) le lit et l'enregistre en mp3 dans temp_audio/ ;
  4. le fichier mp3 est envoye, puis supprime (BackgroundTasks).
GET /health : l'API repond.

Lancement en local, depuis la racine du projet : uvicorn api_service.main:app --port 8000
"""
import logging
import os
import tempfile
import time
from urllib.parse import quote
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from .services.llm_reformulator import ecrire_pitch
from .services.tts_engine import creer_voix

load_dotenv()  # en local : lit la cle OpenAI et l'adresse de la base dans le fichier .env

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # dossier au-dessus de api_service/
# Meme base que le site, avec la meme regle que app_web/config.py : DATABASE_URL sur Render, SQLite en local.
# L'API n'importe pas app_web/config.py : Python executerait d'abord app_web/__init__.py, qui cree tout
# le site Flask (pandas, scikit-learn...) et doublerait la memoire utilisee sur Render.
ADRESSE_BASE = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(RACINE, 'database', 'cvboost.db')
DOSSIER_AUDIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio')  # mp3 temporaires
os.makedirs(DOSSIER_AUDIO, exist_ok=True)

# Les erreurs sont ecrites dans la console : Render les affiche dans l'onglet "Logs"
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')
journal = logging.getLogger('api_service.pitch')
moteur = create_engine(ADRESSE_BASE, pool_pre_ping=True)  # pool_pre_ping : reconnexion si Postgres a coupe
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
        pitch = ecrire_pitch(texte_cv)
    except Exception as erreur:  # cle absente, credit epuise, OpenAI trop lent...
        journal.error('Pitch non ecrit (%s)', type(erreur).__name__)
        raise HTTPException(503, "Le pitch n'a pas pu être préparé.")

    # Etape 3 : la voix, dans un fichier temporaire de temp_audio/ (mkstemp lui donne un nom unique)
    descripteur, chemin = tempfile.mkstemp(suffix='.mp3', dir=DOSSIER_AUDIO)
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
