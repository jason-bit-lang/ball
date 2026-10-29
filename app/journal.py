"""Journal des evenements (connexions, envois de CV) lu ensuite par pipeline/audit_logs.py.

Pourquoi un journal ? Il permet de compter l'usage du site (statistiques de la partie 2) et de reperer
les tentatives de fraude (par exemple, beaucoup d'envois refuses en peu de temps).

Une ligne par evenement, par exemple :
2026-10-26 17:26:01 | UPLOAD_OK | user=3 | ip=127.0.0.1 | file=cv.pdf | ext=pdf | size=48211
"""
import logging
from flask import request
from flask_login import current_user
from pipeline.config import LOG_FILE  # meme chemin pour le site et pour le script d'audit

logger = logging.getLogger('cvboost.evenements')
logger.setLevel(logging.INFO)
logger.propagate = False  # ces lignes ont leur propre format : elles ne passent pas par le journal des erreurs
# "if not logger.handlers" : evite d'ajouter deux fois les memes sorties si le fichier est importe deux fois
if not logger.handlers:
    # Fichier lu par le script d'audit, et console : sur Render, le disque est efface a chaque redemarrage,
    # la console reste lisible dans l'onglet "Logs"
    for handler in [logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]:
        handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', '%Y-%m-%d %H:%M:%S'))
        logger.addHandler(handler)


def clean(value):
    """Empeche un utilisateur de casser le format du journal (caracteres | et retours a la ligne).
    Exemple : un nom de fichier "cv|ip=1.2.3.4" pourrait sinon fausser la ligne lue par l'audit."""
    return str(value).replace('|', '/').replace('\n', ' ').replace('\r', ' ')


def log_event(event, **details):
    """Ecrit un evenement avec l'utilisateur et l'adresse IP de la requete en cours.
    `details` regroupe les informations en plus, par exemple log_event('PITCH', cv=3) -> cv=3."""
    user = current_user.id if current_user.is_authenticated else '-'  # '-' pour un visiteur non connecte
    fields = {'user': user, 'ip': request.remote_addr, **details}
    # Assemble "EVENEMENT | cle=valeur | cle=valeur ..."
    logger.info(' | '.join([event] + [f'{key}={clean(value)}' for key, value in fields.items()]))
