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
│   ├── offres.py        copie des offres (data/) dans la base du site
│   ├── matching.py      moteur de matching CV / offres (TF-IDF)
│   ├── ia.py            assistante DRH : lecture du CV et entretien avec OpenAI
│   ├── static/          style.css, entretien.js
│   └── templates/       base, index, register, login, upload, history, result, offres, offre
├── pipeline/            pipeline de donnees (partie 2)
│   ├── config.py        chemins et reglages communs
│   ├── audit_logs.py    lecture du journal, detection des fraudes, chargement dans analytics.db
│   ├── kpi.py           statistiques d'usage en SQL (GROUP BY, HAVING)
│   ├── nettoyage_offres.py  nettoyage Pandas des offres d'emploi
│   └── dataset_ia.py    jeu de donnees anti-fuite pour le fine-tuning (partie 3)
├── notebooks/           finetuning_lora.ipynb (a ouvrir dans Google Colab)
├── data/                analytics.db, fichiers d'offres, data/ia/ (train, validation, test)
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
python -m pipeline.dataset_ia        # data/offres_propres.csv -> data/ia/*.jsonl (80/10/10 sans fuite)
```

## IA (partie 3)

- **Fine-tuning LoRA** : ouvrir `notebooks/finetuning_lora.ipynb` dans Google Colab (GPU T4), tout executer,
  puis ajouter au depot les deux fichiers telecharges : `data/offres_ia.csv` et `modele/lora_cvboost/`.
- **Matching** : au demarrage, `run.py` copie les offres de `data/` dans la base. Le bouton
  "Rechercher des offres" compare le CV aux offres avec TF-IDF (scikit-learn), sans PyTorch.
- **Assistante DRH** : sur la page d'une offre, "Simulation d'entretien" envoie le CV et l'offre a
  OpenAI (gpt-4o-mini). La cle `OPENAI_API_KEY` doit etre dans `.env`.

Les annonces scannees sont lues par OCR avec Tesseract (optionnel en local) :
- Windows : installer depuis https://github.com/UB-Mannheim/tesseract/wiki en cochant la langue francaise
- Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`

Le scraping tourne aussi tout seul chaque jour sur GitHub Actions
(`.github/workflows/scraping-quotidien.yml`, actif une fois le code fusionne dans `main`).
