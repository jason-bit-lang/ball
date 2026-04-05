import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = 'notre_petit_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path,'cvboost.db')
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 Mo

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_view = 'login'
login_manager.init_app(app)

from .models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from . import routes

