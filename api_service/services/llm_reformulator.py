"""Service 1 du pitch : gpt-4o-mini transforme le texte brut du CV en un discours fluide d'environ 60 mots,
a la premiere personne, qui repond a la question d'entretien "Presentez-vous"."""
from openai import OpenAI

MODELE_TEXTE = 'gpt-4o-mini'
DELAI_TEXTE = 6   # secondes au plus pour ecrire le pitch (il en faut environ 1,5)
CV_MAX = 6000     # caracteres du CV envoyes a OpenAI (un CV plus long est coupe : cout et delai limites)

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


def ecrire_pitch(texte_cv):
    """Renvoie le texte du pitch. Leve une exception si OpenAI ne repond pas (cle absente, credit epuise,
    delai depasse) : main.py l'attrape et previent l'utilisateur."""
    # La cle vient de la variable OPENAI_API_KEY. Aucune nouvelle tentative (max_retries=0) : en cas de
    # panne, l'utilisateur recoit vite un message au lieu d'attendre plus de 10 secondes.
    client = OpenAI(timeout=DELAI_TEXTE, max_retries=0)
    # max_tokens=200 : de la marge pour 60 mots, mais pas de quoi ecrire un long texte (cout et delai)
    reponse = client.chat.completions.create(model=MODELE_TEXTE, max_tokens=200, messages=[
        {'role': 'system', 'content': CONSIGNES},
        {'role': 'user', 'content': texte_cv[:CV_MAX]}])
    return reponse.choices[0].message.content.strip()
