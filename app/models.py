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
    # Le fichier est garde dans la base, pas sur le disque : sur Render, le disque est efface a chaque redemarrage
    contenu = db.Column(db.LargeBinary)
    texte = db.Column(db.Text)  # texte lu une seule fois a l'envoi ; utilise par le matching, l'assistante et le pitch

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Offre(db.Model):
    """Offre d'emploi scrapee, copiee depuis data/offres_propres.csv (voir app/offres.py)."""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    # Textes lus par OCR ou produits par l'IA : leur longueur n'est pas garantie, d'ou db.Text (sans limite).
    # Postgres refuse un texte plus long que la taille d'un db.String ; SQLite, lui, l'accepte sans rien dire.
    titre = db.Column(db.Text, nullable=False)
    entreprise = db.Column(db.Text)
    lieu = db.Column(db.Text)
    description = db.Column(db.Text, nullable=False)
    date_publication = db.Column(db.String(10))  # AAAA-MM-JJ
    date_limite = db.Column(db.String(10))       # AAAA-MM-JJ, lue dans l'annonce (vide si non precisee)
    lien_candidature = db.Column(db.Text)        # site de candidature, ou "mailto:adresse"
    competences = db.Column(db.Text)             # trouvees par le nettoyage Pandas
    titre_ia = db.Column(db.Text)                # trouves par le modele LoRA (traitement par lot sur Colab)
    competences_ia = db.Column(db.Text)


class EntretienVocal(db.Model):
    """Une ligne par entretien vocal lance : limite le nombre d'entretiens payants par jour
    et garde la note de l'evaluation, affichee dans l'historique."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offre_id = db.Column(db.Integer, db.ForeignKey('offre.id'), nullable=False)
    date = db.Column(db.DateTime, default=now_utc)
    note = db.Column(db.Integer)  # note globale /100, remplie a la fin de l'entretien


class Favori(db.Model):
    """Offre mise en favori par un utilisateur (bouton coeur de la page d'une offre)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offre_id = db.Column(db.Integer, db.ForeignKey('offre.id'), nullable=False)
    date = db.Column(db.DateTime, default=now_utc)
    offre = db.relationship('Offre')
    __table_args__ = (db.UniqueConstraint('user_id', 'offre_id'),)  # une offre n'est en favori qu'une fois
