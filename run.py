import os
from sqlalchemy import inspect, text
from app import app, db
from app.ia import extraire_texte
from app.models import Document
from app.offres import synchroniser_offres
from config import DOSSIER


def ajouter_colonnes_manquantes():
    """Base creee avant une mise a jour du site : db.create_all() cree les nouvelles tables mais
    n'ajoute pas les nouvelles colonnes aux tables existantes. On les ajoute ici (elles restent vides)."""
    inspecteur = inspect(db.engine)
    for table in db.metadata.sorted_tables:
        existantes = [colonne['name'] for colonne in inspecteur.get_columns(table.name)]
        for colonne in table.columns:
            if colonne.name not in existantes:
                type_sql = colonne.type.compile(db.engine.dialect)
                db.session.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {colonne.name} {type_sql}'))
    db.session.commit()


def reprendre_anciens_cv():
    """CV envoyes avant la partie 5 : leur fichier etait dans le dossier uploads/.
    On copie le fichier et son texte dans la base (texte vide si le fichier a disparu)."""
    for document in Document.query.filter(Document.texte.is_(None)):
        chemin = os.path.join(DOSSIER, 'uploads', document.stored_filename)
        if os.path.exists(chemin):
            with open(chemin, 'rb') as fichier:
                document.contenu = fichier.read()
        else:
            document.status = 'Fichier introuvable'  # le CV n'apparait plus dans l'historique
        extension = document.stored_filename.rsplit('.', 1)[-1]
        document.texte = extraire_texte(document.contenu or b'', extension)
    db.session.commit()


# Cree les tables si elles n'existent pas encore, puis copie les offres du dossier data/ dans la base
with app.app_context():
    db.create_all()
    ajouter_colonnes_manquantes()
    reprendre_anciens_cv()
    synchroniser_offres()

if __name__ == '__main__':
    # Le mode debug s'active seulement si FLASK_DEBUG=1 dans .env (jamais en production)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
