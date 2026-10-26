import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Charge les variables du fichier .env (SECRET_KEY, OPENAI_API_KEY...)
load_dotenv()

app = Flask(__name__, instance_relative_config=True)

# La cle secrete protege les sessions : elle ne doit jamais etre ecrite dans le code
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY manquante : copiez .env.example en .env et remplissez-la.")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'cvboost.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 Mo maximum par fichier

# Chemins absolus : le site fonctionne quel que soit le dossier d'ou on le lance
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(app.root_path), 'uploads')
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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


from . import routes
