"""Service 2 du pitch : la synthese vocale (TTS, "text to speech") lit le pitch a voix haute.

En ligne, la voix est Denise d'edge-tts : gratuite, environ 1,5 seconde, choisie par l'apprenant apres
ecoute de sage (OpenAI) et de VITS (Coqui TTS). Les mesures de qualite des trois voix sont dans
api_service/metriques_audio.py.
"""
import edge_tts

VOIX = 'fr-FR-DeniseNeural'  # voix feminine francaise d'edge-tts
DELAI_VOIX = 3               # secondes d'attente au plus pour la voix (le site doit repondre en moins de 10 s)


def creer_voix(pitch, chemin):
    """Lit le pitch et l'enregistre dans le fichier mp3 `chemin`.
    Les deux delais evitent d'attendre indefiniment si le service de la voix ne repond pas."""
    edge_tts.Communicate(pitch, VOIX, connect_timeout=DELAI_VOIX, receive_timeout=DELAI_VOIX).save_sync(chemin)
