"""Point de depart du site CVBoost.

- En local : `python run.py` prepare la base puis lance le site sur http://127.0.0.1:5000.
- En ligne (Render, Docker) : gunicorn importe ce fichier (`gunicorn run:app`), ce qui prepare la base
  de la meme facon, puis gunicorn sert le site.

Preparer la base, c'est : creer les tables, ajouter les colonnes apparues dans les mises a jour,
reprendre les anciens CV et copier les offres d'emploi du dossier data/.
"""
import os
from sqlalchemy import inspect, text
from app_web import app, db
from app_web.ia import extraire_texte
from app_web.models import Document
from app_web.offres import synchroniser_offres
from app_web.config import DOSSIER


def ajouter_colonnes_manquantes():
    """Base creee avant une mise a jour du site : db.create_all() cree les nouvelles tables mais
    n'ajoute pas les nouvelles colonnes aux tables existantes. On les ajoute ici (elles restent vides).

    Pourquoi ? Sans cela, il faudrait supprimer la base (et perdre les comptes) a chaque nouvelle colonne."""
    inspecteur = inspect(db.engine)  # outil de SQLAlchemy qui lit la structure de la base reelle
    for table in db.metadata.sorted_tables:  # les tables decrites dans app_web/models.py
        existantes = [colonne['name'] for colonne in inspecteur.get_columns(table.name)]
        for colonne in table.columns:
            if colonne.name not in existantes:
                # Le type est traduit dans le langage de la base utilisee (SQLite ou Postgres)
                type_sql = colonne.type.compile(db.engine.dialect)
                db.session.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {colonne.name} {type_sql}'))
    db.session.commit()


def reprendre_anciens_cv():
    """CV envoyes avant la partie 5 : leur fichier etait dans le dossier uploads/.
    On copie le fichier et son texte dans la base (texte vide si le fichier a disparu).

    Pourquoi ? Depuis la partie 5, les CV sont gardes dans la base, car le disque de Render est efface
    a chaque redemarrage. Les CV deja envoyes sur un PC restent ainsi utilisables."""
    # Un CV sans texte (None) est un ancien CV : les nouveaux ont leur texte des l'envoi
    for document in Document.query.filter(Document.texte.is_(None)):
        chemin = os.path.join(DOSSIER, 'uploads', document.stored_filename)
        if os.path.exists(chemin):
            with open(chemin, 'rb') as fichier:  # 'rb' : lecture des octets bruts (un PDF n'est pas du texte)
                document.contenu = fichier.read()
        else:
            document.status = 'Fichier introuvable'  # le CV n'apparait plus dans l'historique
        extension = document.stored_filename.rsplit('.', 1)[-1]  # "abc.pdf" -> "pdf"
        document.texte = extraire_texte(document.contenu or b'', extension)
    db.session.commit()


# Cree les tables si elles n'existent pas encore, puis copie les offres du dossier data/ dans la base.
# app.app_context() : Flask-SQLAlchemy a besoin de savoir pour quelle application il travaille.
with app.app_context():
    db.create_all()
    ajouter_colonnes_manquantes()
    reprendre_anciens_cv()
    synchroniser_offres()

# Ce bloc ne s'execute qu'avec `python run.py` (pas quand gunicorn importe le fichier)
if __name__ == '__main__':
    # Le mode debug s'active seulement si FLASK_DEBUG=1 dans .env (jamais en production :
    # il afficherait le code et les erreurs a n'importe quel visiteur)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
