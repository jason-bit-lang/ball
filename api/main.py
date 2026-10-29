"""API du pitch vocal de CVBoost (FastAPI).

Le site Flask l'appelle (route /pitch/<id> dans app/routes.py). Elle n'est pas ouverte au public :
elle ecoute seulement sur la machine (127.0.0.1), ou dans le reseau prive de docker-compose.

POST /speak-smart  {"document_id": 3}
  1. lit le texte du CV dans la base de donnees ;
  2. gpt-4o-mini le transforme en pitch oral d'environ 60 mots (reponse a "Presentez-vous") ;
  3. la voix est creee par OpenAI (gpt-4o-mini-tts, voix sage) ou, en secours, par edge-tts (gratuit) ;
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
MODELE_VOIX = 'gpt-4o-mini-tts'
VOIX = 'sage'                        # la meme voix que la recruteuse (choix de l'apprenant)
VOIX_SECOURS = 'fr-FR-DeniseNeural'  # voix feminine francaise d'edge-tts
BUDGET = 9.5    # secondes : le site doit repondre en moins de 10 s
VOIX_MAX = 7    # secondes accordees au plus a la voix OpenAI (environ 5 s pour 60 mots)
SECOURS = 2     # secondes toujours gardees pour la voix de secours (edge-tts met environ 2 s)
CV_MAX = 6000   # caracteres du CV envoyes a OpenAI

# Consignes reprises du module 3 (coach professionnel), ramenees a environ 60 mots
CONSIGNES = """Tu es un coach professionnel.
Tache : transforme le texte du CV fourni en un pitch oral captivant, a la premiere personne, qui repond
a la question d'entretien "Presentez-vous".
Contraintes :
- Redige un texte continu, sans puces, sans titres ni symboles speciaux.
- Utilise des phrases courtes et fluides, faciles a lire a voix haute.
- Entre 50 et 60 mots, en 4 ou 5 phrases courtes.
- N'invente rien : utilise seulement ce qui figure dans le CV.
- Reponds en francais."""
TON = "Parle en français, d'une voix posée, chaleureuse et assurée."

# Les erreurs sont ecrites dans la console : Render les affiche dans l'onglet "Logs"
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')
journal = logging.getLogger('api.pitch')
moteur = create_engine(ADRESSE_BASE, pool_pre_ping=True)
app = FastAPI(title='CVBoost - pitch vocal')


class Demande(BaseModel):
    document_id: int


def texte_du_cv(document_id):
    """Texte du CV enregistre a l'envoi (table document), ou None si le CV n'existe pas."""
    with moteur.connect() as connexion:
        ligne = connexion.execute(text('SELECT texte FROM document WHERE id = :id'), {'id': document_id}).first()
    return ligne[0] if ligne else None


def ecrire_pitch(client, texte_cv):
    """Etape 2 : le CV brut devient un discours fluide."""
    reponse = client.chat.completions.create(model=MODELE_TEXTE, max_tokens=200, messages=[
        {'role': 'system', 'content': CONSIGNES},
        {'role': 'user', 'content': texte_cv[:CV_MAX]}])
    return reponse.choices[0].message.content.strip()


def voix_openai(client, pitch, chemin, limite):
    """Le son arrive morceau par morceau : on l'ecrit dans le fichier et on abandonne si l'heure limite est passee.
    (Le "timeout" d'OpenAI ne suffit pas : il limite l'attente de chaque morceau, pas la duree totale.)"""
    with client.audio.speech.with_streaming_response.create(
            model=MODELE_VOIX, voice=VOIX, input=pitch, instructions=TON, response_format='mp3',
            timeout=limite - time.time()) as reponse:
        with open(chemin, 'wb') as fichier:
            for morceau in reponse.iter_bytes():
                if time.time() > limite:
                    raise TimeoutError('voix OpenAI trop lente')
                fichier.write(morceau)


def creer_voix(client, pitch, chemin, limite):
    """Etape 3 : voix OpenAI si elle est prete avant l'heure limite, sinon voix de secours edge-tts.
    Renvoie le nom du moteur utilise."""
    if limite - time.time() >= 1:
        try:
            voix_openai(client, pitch, chemin, limite)
            return 'openai'
        except Exception as erreur:  # heure limite depassee, credit epuise, reseau coupe...
            journal.warning('Voix OpenAI indisponible (%s) : voix de secours', type(erreur).__name__)
    edge_tts.Communicate(pitch, VOIX_SECOURS, connect_timeout=SECOURS, receive_timeout=SECOURS).save_sync(chemin)
    return 'edge-tts'


@app.post('/speak-smart')
def speak_smart(demande: Demande, taches: BackgroundTasks):
    debut = time.time()
    texte_cv = texte_du_cv(demande.document_id)
    if not texte_cv:
        raise HTTPException(404, 'CV introuvable.')
    try:
        client = OpenAI(timeout=BUDGET - SECOURS, max_retries=0)  # la cle vient de OPENAI_API_KEY
        pitch = ecrire_pitch(client, texte_cv)
    except Exception as erreur:
        journal.error('Pitch non ecrit (%s)', type(erreur).__name__)
        raise HTTPException(503, "Le pitch n'a pas pu être préparé.")

    # Fichier temporaire : il est supprime juste apres l'envoi
    descripteur, chemin = tempfile.mkstemp(suffix='.mp3')
    os.close(descripteur)
    # Heure limite de la voix OpenAI : 7 s au plus, et toujours 2 s de marge pour la voix de secours
    limite = min(time.time() + VOIX_MAX, debut + BUDGET - SECOURS)
    try:
        moteur_voix = creer_voix(client, pitch, chemin, limite)
    except Exception as erreur:
        os.remove(chemin)
        journal.error('Voix non creee (%s)', type(erreur).__name__)
        raise HTTPException(503, "La voix du pitch n'a pas pu être créée.")
    taches.add_task(os.remove, chemin)
    journal.info('Pitch du CV %s : %s mots, voix %s, %.1f s', demande.document_id, len(pitch.split()),
                 moteur_voix, time.time() - debut)
    # Le texte du pitch accompagne le son dans un en-tete HTTP (accents encodes avec quote)
    return FileResponse(chemin, media_type='audio/mpeg',
                        headers={'X-Pitch-Texte': quote(pitch), 'X-Voix': moteur_voix})


@app.get('/health')
def health():
    return {'statut': 'ok'}
