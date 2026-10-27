from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


def now_utc():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    documents = db.relationship('Document', backref='owner', lazy=True)

    # Le mot de passe n'est jamais stocke en clair, seulement son hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=now_utc)
    status = db.Column(db.String(50), default="En attente d'analyse")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Offre(db.Model):
    """Offre d'emploi scrapee, copiee depuis data/offres_propres.csv (voir app/offres.py)."""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    titre = db.Column(db.String(300), nullable=False)
    entreprise = db.Column(db.String(200))
    lieu = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    date_publication = db.Column(db.String(10))  # AAAA-MM-JJ
    lien_candidature = db.Column(db.String(500))
    competences = db.Column(db.String(500))      # trouvees par le nettoyage Pandas
    titre_ia = db.Column(db.String(300))         # trouves par le modele LoRA (traitement par lot sur Colab)
    competences_ia = db.Column(db.String(500))
