import os
from app import app, db

# Cree les tables si elles n'existent pas encore
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Le mode debug s'active seulement si FLASK_DEBUG=1 dans .env (jamais en production)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
