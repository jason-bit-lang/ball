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
│   ├── journal.py       journal des connexions et des envois de CV
│   ├── static/          style.css, style.js
│   └── templates/       base, index, register, login, upload, history, result
├── pipeline/            pipeline de donnees (partie 2)
│   ├── config.py        chemins et reglages communs
│   ├── audit_logs.py    lecture du journal, detection des fraudes, chargement dans analytics.db
│   ├── kpi.py           statistiques d'usage en SQL (GROUP BY, HAVING)
│   └── nettoyage_offres.py  nettoyage Pandas des offres d'emploi
├── data/                analytics.db et fichiers d'offres
├── logs/                journal du site (non versionne)
├── database/            base SQLite (creee automatiquement, non versionnee)
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
cp .env.example .env    # puis remplir SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")
python run.py
```

L'application est ensuite disponible sur http://127.0.0.1:5000.

## Pipeline de donnees

```bash
python -m pipeline.audit_logs        # lit logs/evenements.log, detecte les fraudes, remplit data/analytics.db
python -m pipeline.kpi               # affiche les statistiques d'usage
python -m pipeline.scraper 5        # 5 pages d'offres de mediacongo.net -> data/offres_brutes.csv
python -m pipeline.nettoyage_offres  # data/offres_brutes.csv -> data/offres_propres.csv
```

Les annonces scannees sont lues par OCR avec Tesseract (optionnel en local) :
- Windows : installer depuis https://github.com/UB-Mannheim/tesseract/wiki en cochant la langue francaise
- Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`

Le scraping tourne aussi tout seul chaque jour sur GitHub Actions
(`.github/workflows/scraping-quotidien.yml`, actif une fois le code fusionne dans `main`).
