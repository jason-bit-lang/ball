import os
from app import app, db
from app.offres import synchroniser_offres

# Cree les tables si elles n'existent pas encore, puis copie les offres du dossier data/ dans la base
with app.app_context():
    db.create_all()
    synchroniser_offres()

if __name__ == '__main__':
    # Le mode debug s'active seulement si FLASK_DEBUG=1 dans .env (jamais en production)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
