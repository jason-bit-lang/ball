"""Journal des evenements (connexions, envois de CV) lu ensuite par pipeline/audit_logs.py.

Une ligne par evenement, par exemple :
2026-10-26 17:26:01 | UPLOAD_OK | user=3 | ip=127.0.0.1 | file=cv.pdf | ext=pdf | size=48211
"""
import logging
from flask import request
from flask_login import current_user
from pipeline.config import LOG_FILE  # meme chemin pour le site et pour le script d'audit

logger = logging.getLogger('cvboost.evenements')
logger.setLevel(logging.INFO)
logger.propagate = False  # n'ecrit pas aussi dans la console
if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)


def clean(value):
    """Empeche un utilisateur de casser le format du journal (caracteres | et retours a la ligne)."""
    return str(value).replace('|', '/').replace('\n', ' ').replace('\r', ' ')


def log_event(event, **details):
    """Ecrit un evenement avec l'utilisateur et l'adresse IP de la requete en cours."""
    user = current_user.id if current_user.is_authenticated else '-'
    fields = {'user': user, 'ip': request.remote_addr, **details}
    logger.info(' | '.join([event] + [f'{key}={clean(value)}' for key, value in fields.items()]))
