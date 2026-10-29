import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from config import ADRESSE_BASE, DOSSIER  # config.py charge aussi le fichier .env

# Journal des erreurs : ecrit dans la console, que Render affiche dans l'onglet "Logs"
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')

# La base SQLite locale est rangee dans database/
app = Flask(__name__, instance_path=os.path.join(DOSSIER, 'database'))

# Sur Render, le site est derriere un proxy : on lit la vraie adresse IP du visiteur
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# La cle secrete protege les sessions : elle ne doit jamais etre ecrite dans le code
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY manquante : copiez .env.example en .env et remplissez-la.")

# Cookie de session : jamais lisible par JavaScript, jamais envoye depuis un autre site, et en ligne
# (Render ajoute la variable RENDER=true) seulement sur une connexion chiffree HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER') == 'true'

app.config['SQLALCHEMY_DATABASE_URI'] = ADRESSE_BASE
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}  # reconnexion si Postgres a coupe la liaison
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 Mo maximum par fichier
os.makedirs(app.instance_path, exist_ok=True)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)  # bloque les formulaires envoyes depuis un autre site

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'

from .models import User


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Importe les pages a la fin : routes.py a besoin de `app` et `db` definis plus haut
from . import routes  # noqa: F401
