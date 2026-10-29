"""Qualite des voix du pitch : WER et CER (mesures automatiques), MOS (notes d'ecoute).

- WER (Word Error Rate, taux d'erreur sur les mots) : une voix lit un pitch, puis un modele de
  transcription (gpt-4o-mini-transcribe) ecrit ce qu'il entend. On compte les mots faux, oublies ou
  ajoutes par rapport au texte d'origine, divises par le nombre de mots. 0 % = voix parfaitement comprise.
- CER (Character Error Rate) : le meme calcul lettre par lettre (plus fin : un accent oublie compte).
- MOS (Mean Opinion Score) : des personnes ecoutent chaque extrait sans savoir quelle voix parle et
  donnent une note de 1 (tres mauvais) a 5 (excellent). Le MOS d'une voix est la moyenne de ses notes.

Voix comparees : sage (OpenAI, utilisee en ligne), Denise (edge-tts, voix de secours en ligne) et VITS
(Coqui TTS, modele libre qui tourne en local ; mesure seulement si la bibliotheque TTS est installee).

Installation (a part, hors du site) : pip install -r requirements.txt jiwer==4.0.0
et, pour VITS, dans un environnement separe (PyTorch) : pip install "coqui-tts[codec]==0.28.0"
Resultats du 29/10 (5 pitchs par voix) : WER sage 4,2 %, Denise 6,1 %, VITS 7,3 % ; CER 1,7 %, 2,1 %, 2,0 %.
Les erreurs viennent surtout des noms congolais (Kongo entendu "Congo", Nsimba, Mukendi, Ngaliema).

Utilisation (hors du site, sur un PC ou sur Colab) :
  python -m api_service.metriques_audio        cree les extraits dans data/audio/, mesure WER et CER
  python -m api_service.metriques_audio mos    moyenne des notes ecrites dans data/audio/notes_mos.csv
"""
import os
import random
import re
import sys
import time
import edge_tts
import jiwer
import pandas as pd
from openai import OpenAI
from data_pipeline.config import DATA_DIR

DOSSIER_AUDIO = os.path.join(DATA_DIR, 'audio')        # extraits a ecouter (non versionnes)
RESULTATS = os.path.join(DATA_DIR, 'metriques_audio.csv')
NOTES_MOS = os.path.join(DOSSIER_AUDIO, 'notes_mos.csv')

# Cinq pitchs de test (personnes fictives), comme ceux produits par l'API du pitch.
# Textes fixes : les memes phrases pour toutes les voix, sinon la comparaison ne serait pas juste.
PITCHS = [
    "Je m'appelle Grace Mbuyi, je suis comptable à Kinshasa. Chez Bralima, je gère la comptabilité générale "
    "selon les normes OHADA, les déclarations fiscales et les clôtures mensuelles sur SAGE. Avant cela, j'ai été "
    "assistante comptable chez Rawbank. Je parle français, anglais et lingala, et j'aime rendre les chiffres clairs.",
    "Je suis Patrick Ilunga, développeur web depuis quatre ans. Je crée des applications avec Python, Django et "
    "JavaScript, et je gère des bases de données PostgreSQL. À Lubumbashi, j'ai conçu une plateforme de paiement "
    "mobile utilisée par trois mille clients. J'aime résoudre des problèmes concrets et travailler en équipe.",
    "Je m'appelle Sarah Kabeya, logisticienne. Pendant six ans, j'ai organisé l'approvisionnement de projets "
    "humanitaires dans le Nord-Kivu : achats, stocks et transport vers des zones difficiles d'accès. Je maîtrise "
    "Excel et les procédures des bailleurs de fonds. Je suis rigoureuse, calme et toujours prête à partir sur le terrain.",
    "Je suis Jonathan Mukendi, infirmier diplômé de l'Institut supérieur des techniques médicales de Kinshasa. "
    "Depuis cinq ans, je travaille aux urgences de l'hôpital de Ngaliema. Je soigne, j'accompagne les familles et "
    "je forme les stagiaires. Je cherche un poste où la qualité des soins passe avant tout.",
    "Je m'appelle Ruth Nsimba, chargée de projet en développement rural. J'ai suivi des projets agricoles financés "
    "par la Banque mondiale au Kongo Central, du budget jusqu'au rapport final. Je sais animer des réunions avec "
    "les communautés et suivre des indicateurs. Je veux mettre cette expérience au service de votre organisation.",
]


def voix_sage(texte, chemin):
    """Voix sage d'OpenAI (payante, environ 5 s) : celle de la recruteuse de l'entretien."""
    reponse = OpenAI().audio.speech.create(model='gpt-4o-mini-tts', voice='sage', input=texte,
                                           response_format='mp3')
    reponse.write_to_file(chemin)


def voix_denise(texte, chemin):
    """Voix Denise d'edge-tts (gratuite, environ 1 s) : celle du pitch sur le site."""
    edge_tts.Communicate(texte, 'fr-FR-DeniseNeural').save_sync(chemin)


def voix_disponibles():
    """Nom de la voix -> (fonction qui cree l'extrait, extension du fichier)."""
    voix = {'sage (OpenAI)': (voix_sage, 'mp3'), 'Denise (edge-tts)': (voix_denise, 'mp3')}
    try:
        from TTS.api import TTS  # Coqui TTS : installe seulement en local ou sur Colab (PyTorch)
    except ImportError:
        print('Coqui TTS absent : la voix VITS est ignoree (pip install coqui-tts).')
        return voix
    modele = TTS('tts_models/fr/css10/vits', progress_bar=False)  # modele francais, charge une seule fois

    def voix_vits(texte, chemin):
        """Voix VITS de Coqui TTS : modele libre qui tourne sur l'ordinateur, sans Internet."""
        modele.tts_to_file(text=texte, file_path=chemin)

    voix['VITS (Coqui TTS)'] = (voix_vits, 'wav')
    return voix


def normaliser(texte):
    """Minuscules, sans ponctuation : on compare les mots, pas la facon de les ecrire."""
    texte = re.sub(r"[’'\-]", ' ', texte.lower())  # "j'ai" -> "j ai", "Nord-Kivu" -> "nord kivu"
    texte = re.sub(r'[^\w\s]', '', texte)          # retire la ponctuation restante
    return ' '.join(texte.split())


def transcrire(chemin):
    """Ce que le modele de transcription entend dans l'extrait audio (il joue le role d'un auditeur)."""
    with open(chemin, 'rb') as fichier:
        return OpenAI().audio.transcriptions.create(model='gpt-4o-mini-transcribe', file=fichier, language='fr').text


def mesurer():
    """Cree chaque extrait, le fait transcrire et calcule WER et CER. Les fichiers portent un numero au hasard :
    a l'ecoute (MOS), on ne sait pas quelle voix parle."""
    os.makedirs(DOSSIER_AUDIO, exist_ok=True)
    voix = voix_disponibles()
    extraits = [(nom, numero) for nom in voix for numero in range(len(PITCHS))]
    random.Random(2026).shuffle(extraits)  # ordre melange, toujours le meme d'une fois sur l'autre
    lignes = []
    for rang, (nom, numero) in enumerate(extraits, start=1):
        creer, extension = voix[nom]
        fichier = f'extrait_{rang:02d}.{extension}'
        debut = time.time()
        creer(PITCHS[numero], os.path.join(DOSSIER_AUDIO, fichier))
        secondes = time.time() - debut
        transcription = transcrire(os.path.join(DOSSIER_AUDIO, fichier))
        # reference : ce qui devait etre dit ; hypothese : ce qui a ete compris
        reference, hypothese = normaliser(PITCHS[numero]), normaliser(transcription)
        lignes.append({'fichier': fichier, 'voix': nom, 'pitch': numero + 1, 'secondes': round(secondes, 2),
                       'wer': jiwer.wer(reference, hypothese), 'cer': jiwer.cer(reference, hypothese),
                       'transcription': transcription})
        print(f"{fichier} : {nom}, pitch {numero + 1}, {secondes:.1f} s, WER {lignes[-1]['wer']:.1%}")
    resultats = pd.DataFrame(lignes)
    resultats.to_csv(RESULTATS, index=False)
    # Fiche de notes a remplir par les auditeurs (une ligne par auditeur et par extrait)
    pd.DataFrame({'fichier': sorted(resultats['fichier']), 'auditeur': '', 'note': ''}).to_csv(NOTES_MOS, index=False)
    # Moyenne de chaque mesure par voix (comme un GROUP BY en SQL)
    bilan = resultats.groupby('voix').agg(secondes=('secondes', 'mean'), wer=('wer', 'mean'), cer=('cer', 'mean'))
    print('\nMoyennes par voix (WER et CER : plus c\'est bas, mieux c\'est)')
    print(bilan.round(3).to_string())
    print(f'\nPour le MOS : ecouter les extraits de {DOSSIER_AUDIO}, noter de 1 a 5 dans {NOTES_MOS},'
          ' puis lancer : python -m api_service.metriques_audio mos')


def mos():
    """MOS de chaque voix : moyenne des notes de 1 a 5 donnees par les auditeurs."""
    notes = pd.read_csv(NOTES_MOS).dropna(subset=['note'])  # lignes pas encore notees : ignorees
    # Les notes ne disent que le nom du fichier : on retrouve la voix grace au fichier des resultats
    notes = notes.merge(pd.read_csv(RESULTATS)[['fichier', 'voix']], on='fichier')
    bilan = notes.groupby('voix').agg(mos=('note', 'mean'), nombre_de_notes=('note', 'count'))
    print(bilan.round(2).to_string())


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'mos':
        mos()
    else:
        mesurer()
