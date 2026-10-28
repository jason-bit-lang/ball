import os
from sqlalchemy import inspect, text
from app import app, db
from app.offres import synchroniser_offres


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


# Cree les tables si elles n'existent pas encore, puis copie les offres du dossier data/ dans la base
with app.app_context():
    db.create_all()
    ajouter_colonnes_manquantes()
    synchroniser_offres()

if __name__ == '__main__':
    # Le mode debug s'active seulement si FLASK_DEBUG=1 dans .env (jamais en production)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
