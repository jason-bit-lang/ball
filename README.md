[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/89Qc2aKD)

# CVBoost

Plateforme web Flask : l'utilisateur s'inscrit, televerse son CV, recoit des offres d'emploi
qui correspondent a son profil et peut simuler un entretien avec une assistante DRH (IA).

Le detail des objectifs et des etapes du projet se trouve dans `CLAUDE.md`.

## Technologies

| Composant            | Technologie                                        |
| -------------------- | -------------------------------------------------- |
| Site                 | Python / Flask, gunicorn                           |
| Authentification     | Flask-Login, hashage Werkzeug, protection CSRF     |
| Base de donnees      | SQLite en local, Postgres sur Render (SQLAlchemy)  |
| Frontend             | HTML5 / CSS3 / Jinja2 / JavaScript                 |
| Matching CV / offres | TF-IDF (scikit-learn)                              |
| Assistante DRH       | OpenAI (gpt-4o-mini, gpt-live-1)                   |
| Pitch vocal          | FastAPI, OpenAI gpt-4o-mini-tts, secours edge-tts  |
| Deploiement          | Docker, docker-compose, GitHub Actions, Render     |

## Structure

```
.
├── app/                 le site (Flask)
│   ├── __init__.py      configuration Flask, base de donnees, Flask-Login
│   ├── models.py        tables User, Document (le CV et son texte), Offre, Favori, EntretienVocal
│   ├── routes.py        pages et logique
│   ├── journal.py       journal des connexions et des envois de CV
│   ├── offres.py        copie des offres (data/) dans la base du site
│   ├── matching.py      moteur de matching CV / offres (TF-IDF)
│   ├── ia.py            assistante DRH : lecture du CV et entretien avec OpenAI
│   ├── affichage.py     dates en francais, echeances, annonce en sections, maniere de postuler
│   ├── static/          style.css, site.js, envoi.js, offre.js, entretien.js
│   └── templates/       base, macros, icones, index, register, login, upload, resultats, offre, history, erreur
├── api/main.py          API du pitch vocal (FastAPI) : /speak-smart et /health
├── pipeline/            pipeline de donnees (partie 2)
│   ├── config.py        chemins et reglages communs
│   ├── audit_logs.py    lecture du journal, detection des fraudes, chargement dans analytics.db
│   ├── kpi.py           statistiques d'usage en SQL (GROUP BY, HAVING)
│   ├── nettoyage_offres.py  nettoyage Pandas des offres d'emploi
│   ├── dataset_ia.py    jeu de donnees anti-fuite pour le fine-tuning (partie 3)
│   └── finetuning_lora.py   fine-tuning LoRA, score SacreBLEU, traitement par lot des offres
├── notebooks/           finetuning_lora.ipynb : lance finetuning_lora.py sur Google Colab (GPU)
├── modele/              adaptateur LoRA entraine (lora_cvboost/)
├── data/                analytics.db, fichiers d'offres, data/ia/ (train, validation, test)
├── logs/                journal du site (non versionne)
├── database/            base SQLite locale (creee automatiquement, non versionnee)
├── .github/workflows/   scraping quotidien ; tests puis deploiement sur Render
├── config.py            reglages communs au site et a l'API (adresse de la base, de l'API)
├── Dockerfile           image du site et de l'API ; .dockerignore : ce qui n'y entre pas
├── docker-compose.yml   en local : site, API et base Postgres separes
├── demarrer.sh          sur Render : lance l'API puis le site
├── .env.example         modele du fichier .env
├── requirements.txt
└── run.py               cree les tables, reprend les anciens CV, copie les offres, lance le site
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
Pour le pitch vocal, lancer aussi l'API dans un second terminal (meme dossier, meme venv) :

```bash
uvicorn api.main:app --port 8000
```

Avec Docker (site, API et base Postgres, chacun dans son conteneur) :

```bash
docker compose up --build      # puis ouvrir http://localhost:5000 ; arret : docker compose down
```

## Mise en ligne (Render)

Un seul service Render (offre gratuite) construit le `Dockerfile` et lance `demarrer.sh` (API + site),
avec une base Postgres Render. Variables a renseigner sur Render : `SECRET_KEY`, `OPENAI_API_KEY`,
`DATABASE_URL`. A chaque envoi sur la branche publiee, GitHub Actions construit l'image, verifie que le
site demarre, puis appelle le Deploy Hook de Render (secret GitHub `RENDER_DEPLOY_HOOK`).
La route `/health` indique l'etat du site, de la base et de l'API.

## Pipeline de donnees

```bash
python -m pipeline.audit_logs        # lit logs/evenements.log, detecte les fraudes, remplit data/analytics.db
python -m pipeline.kpi               # affiche les statistiques d'usage
python -m pipeline.scraper 5        # 5 pages d'offres de mediacongo.net -> data/offres_brutes.csv
python -m pipeline.nettoyage_offres  # data/offres_brutes.csv -> data/offres_propres.csv
python -m pipeline.dataset_ia        # data/offres_propres.csv -> data/ia/*.jsonl (80/10/10 sans fuite)
```

## IA (partie 3)

- **Fine-tuning LoRA** : le code est dans `pipeline/finetuning_lora.py`. Sur Google Colab (GPU T4) : ouvrir
  `notebooks/finetuning_lora.ipynb` et tout executer, puis ajouter au depot `data/offres_ia.csv` et
  `modele/lora_cvboost/`. En local : `pip install torch -r requirements-ia.txt` puis
  `python -m pipeline.finetuning_lora` (plus lent sans GPU). Ces bibliotheques ne sont pas utiles au site.
- **Matching** : au demarrage, `run.py` copie les offres de `data/` dans la base. Le bouton
  "Rechercher des offres" compare le CV aux offres avec TF-IDF (scikit-learn), sans PyTorch.
- **Assistante DRH** (`ASSISTANTE_ACTIVE` dans `app/routes.py`) : sur la page d'une offre, analyse du CV
  (gpt-4o-mini), entretien vocal en direct (gpt-live-1, micro necessaire) puis evaluation.
  La cle `OPENAI_API_KEY` doit etre dans `.env`.
- **Pitch vocal** (partie 5) : reponse modele a "Presentez-vous", faite a partir du CV (50 a 60 mots),
  lue avec la voix sage d'OpenAI, ou par edge-tts en secours.

Les annonces scannees sont lues par OCR avec Tesseract (optionnel en local) :
- Windows : installer depuis https://github.com/UB-Mannheim/tesseract/wiki en cochant la langue francaise
- Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`

Le scraping tourne aussi tout seul chaque jour sur GitHub Actions
(`.github/workflows/scraping-quotidien.yml`, actif une fois le code fusionne dans `main`).
