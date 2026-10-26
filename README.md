[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/89Qc2aKD)

# CVBoost

Plateforme web Flask : l'utilisateur s'inscrit, televerse son CV, recoit des offres d'emploi
qui correspondent a son profil et peut simuler un entretien avec une assistante DRH (IA).

Le detail des objectifs et des etapes du projet se trouve dans `CLAUDE.md`.

## Technologies (partie 1)

| Composant            | Technologie           |
| -------------------- | --------------------- |
| Backend              | Python / Flask        |
| Authentification     | Flask-Login           |
| Hashage mot de passe | Werkzeug              |
| Base de donnees      | SQLite                |
| ORM                  | Flask-SQLAlchemy      |
| Frontend             | HTML5 / CSS3 / Jinja2 |
| Securite fichiers    | Renommage UUID        |

## Structure

```
.
├── app/
│   ├── __init__.py      configuration Flask, base de donnees, Flask-Login
│   ├── models.py        tables User et Document
│   ├── routes.py        pages et logique
│   ├── forms.py
│   ├── static/          style.css, style.js
│   └── templates/       base, index, register, login, upload, history, result
├── instance/            base SQLite (creee automatiquement, non versionnee)
├── uploads/             CV televerses (non versionnes)
├── .env.example         modele du fichier .env
├── requirements.txt
└── run.py
```

## Lancer le projet en local

```bash
python -m venv venv
# Windows : venv\Scripts\activate    Linux/Mac : source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # puis remplir les valeurs
python run.py
```

L'application est ensuite disponible sur http://127.0.0.1:5000.
