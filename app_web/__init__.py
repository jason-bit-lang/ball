"""Creation de l'application Flask et de ses outils (base de donnees, connexion, protection CSRF).

Ce fichier est lu en premier quand on importe le dossier app_web/ : il cree `app` (le site) et `db`
(la base), que tous les autres fichiers importent ensuite.
"""
import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import ADRESSE_BASE, DOSSIER  # config.py charge aussi le fichier .env

# Journal des erreurs : ecrit dans la console, que Render affiche dans l'onglet "Logs".
# Chaque ligne commence par la date et le niveau (INFO, WARNING, ERROR) pour retrouver un probleme.
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')

# La base SQLite locale est rangee dans database/ (Flask appelle ce dossier "instance_path")
app = Flask(__name__, instance_path=os.path.join(DOSSIER, 'database'))

# Sur Render, le site est derriere un proxy : on lit la vraie adresse IP du visiteur
# (sinon le journal noterait l'adresse du proxy pour tout le monde)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# La cle secrete protege les sessions : elle ne doit jamais etre ecrite dans le code.
# Sans elle, n'importe qui pourrait fabriquer un faux cookie de connexion : le site refuse de demarrer.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY manquante : copiez .env.example en .env et remplissez-la.")

# Cookie de session : jamais lisible par JavaScript, jamais envoye depuis un autre site, et en ligne
# (Render ajoute la variable RENDER=true) seulement sur une connexion chiffree HTTPS.
# En local, le site est en http : un cookie "Secure" n'y serait jamais envoye, d'ou la condition.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER') == 'true'

app.config['SQLALCHEMY_DATABASE_URI'] = ADRESSE_BASE
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}  # reconnexion si Postgres a coupe la liaison
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # option inutile qui consomme de la memoire
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 Mo maximum par fichier (au-dela : erreur 413)
os.makedirs(app.instance_path, exist_ok=True)  # cree database/ s'il n'existe pas encore

db = SQLAlchemy(app)
csrf = CSRFProtect(app)  # bloque les formulaires envoyes depuis un autre site

# Flask-Login retient qui est connecte. Une page protegee (@login_required) renvoie un visiteur
# non connecte vers la page 'login', avec ce message.
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

# Importe ici (et pas en haut) : models.py a besoin de `db`, cree juste au-dessus
from .models import User


@login_manager.user_loader
def load_user(user_id):
    """A chaque page, Flask-Login retrouve l'utilisateur connecte grace au numero garde dans la session."""
    return db.session.get(User, int(user_id))


# Importe les pages a la fin : routes.py a besoin de `app` et `db` definis plus haut
from . import routes  # noqa: F401
