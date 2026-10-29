[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/89Qc2aKD)

# CVBoost

Plateforme web Flask : l'utilisateur s'inscrit, televerse son CV, recoit des offres d'emploi
qui correspondent a son profil, peut simuler un entretien avec une assistante DRH (IA) et ecouter
un pitch vocal tire de son CV.

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
| Fine-tuning          | flan-t5-small, LoRA (PEFT), SacreBLEU              |
| Pitch vocal          | FastAPI, OpenAI gpt-4o-mini, voix Denise (edge-tts)|
| Deploiement          | Docker, docker-compose, GitHub Actions, Render     |

## Structure (architecture de la formation)

```
cvboost_enterprise/
├── .github/workflows/
│   ├── deploy.yml           CI/CD : construit l'image Docker, test de demarrage, puis deploiement Render
│   └── scraping.yml         scraping quotidien des offres (actif une fois le code fusionne dans main)
├── app_web/                 application Flask (sprint 1 et assistante DRH)
│   ├── static/              style.css, site.js, envoi.js, offre.js, entretien.js
│   ├── templates/           base, macros, icones, index, register, login, upload, resultats, offre, history, erreur
│   ├── models.py            tables User, Document (le CV et son texte), Offre, Favori, EntretienVocal
│   ├── routes.py            pages et logique
│   ├── ia.py                connecteur OpenAI : analyse du CV, entretien vocal, evaluation (sprint 3)
│   ├── config.py            reglages du site (adresse de la base, de l'API)
│   ├── __init__.py          cree le site Flask, la base, la connexion et la protection CSRF
│   ├── matching.py          moteur de matching CV / offres (TF-IDF)
│   ├── affichage.py         dates en francais, echeances, annonce en sections, maniere de postuler
│   ├── journal.py           journal des connexions et des envois de CV
│   └── offres.py            copie des offres (data/) dans la base du site
├── data_pipeline/           donnees et scraping (sprint 2)
│   ├── logs_parser.py       lecture du journal, detection des fraudes, chargement dans analytics.db
│   ├── scraper_jobs.py      collecte des offres de mediacongo.net (BeautifulSoup, OCR)
│   ├── pandas_cleaning.py   nettoyage Pandas des offres (doublons, salaires, competences, dates)
│   ├── kpi.py               statistiques d'usage en SQL (GROUP BY, HAVING)
│   └── config.py            chemins partages par les donnees et l'IA
├── ai_engine/               fine-tuning et NLP (sprint 3)
│   ├── prepare_dataset.py   jeux train / validation / test sans fuite (SHA-256, 80/10/10, assertions)
│   ├── train_lora.py        fine-tuning LoRA de flan-t5-small
│   ├── evaluate_model.py    score SacreBLEU avec et sans LoRA, traitement par lot des offres
│   ├── etiquettes_ia.py     competences des offres relues par gpt-4o-mini (corriges de l'entrainement)
│   ├── finetuning_lora.ipynb  lance l'entrainement et l'evaluation sur Google Colab (GPU)
│   └── lora_cvboost/        adaptateur LoRA entraine (1,4 Mo)
├── api_service/             orchestrateur FastAPI (sprint 4)
│   ├── main.py              route POST /speak-smart et /health
│   ├── services/
│   │   ├── llm_reformulator.py  le CV devient un pitch d'environ 60 mots (gpt-4o-mini)
│   │   └── tts_engine.py        le pitch est lu par la voix Denise (edge-tts)
│   ├── temp_audio/          mp3 temporaires, supprimes apres l'envoi
│   └── metriques_audio.py   qualite des voix : WER, CER et MOS
├── database/                cvboost.db (site) et analytics.db (statistiques), crees automatiquement,
│                            jamais envoyes sur GitHub (donnees personnelles)
├── data/                    offres (brutes, propres, resultats du LoRA), data/ia/ (train, validation, test)
├── Dockerfile               image du site et de l'API ; .dockerignore : ce qui n'y entre pas
├── docker-compose.yml       en local : site, API et base Postgres separes
├── demarrer.sh              sur Render : lance l'API puis le site
├── run.py                   cree les tables, reprend les anciens CV, copie les offres, lance le site
├── requirements.txt         bibliotheques du site et de l'API
├── requirements-ia.txt      bibliotheques du fine-tuning (PyTorch), jamais installees sur Render
├── .env.example             modele du fichier .env
└── README.md
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
uvicorn api_service.main:app --port 8000
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

## Donnees (sprint 2)

```bash
python -m data_pipeline.logs_parser      # lit logs/evenements.log, detecte les fraudes, remplit database/analytics.db
python -m data_pipeline.kpi              # affiche les statistiques d'usage
python -m data_pipeline.scraper_jobs 5   # 5 pages d'offres de mediacongo.net -> data/offres_brutes.csv
python -m data_pipeline.pandas_cleaning  # data/offres_brutes.csv -> data/offres_propres.csv
```

Les annonces scannees sont lues par OCR avec Tesseract (optionnel en local) :
- Windows : installer depuis https://github.com/UB-Mannheim/tesseract/wiki en cochant la langue francaise
- Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`

## IA (sprint 3)

```bash
pip install torch -r requirements-ia.txt  # une seule fois, hors du site
python -m ai_engine.prepare_dataset      # data/offres_propres.csv -> data/ia/*.jsonl (80/10/10 sans fuite)
python -m ai_engine.train_lora           # fine-tuning LoRA -> ai_engine/lora_cvboost/ (GPU conseille)
python -m ai_engine.evaluate_model       # SacreBLEU avec et sans LoRA, puis data/offres_ia.csv
```

- Sur Google Colab (GPU T4) : ouvrir `ai_engine/finetuning_lora.ipynb` et tout executer.
- **Matching** : au demarrage, `run.py` copie les offres de `data/` dans la base. La page des opportunites
  compare le CV aux offres avec TF-IDF (scikit-learn), sans PyTorch.
- **Assistante DRH** (`ASSISTANTE_ACTIVE` dans `app_web/routes.py`) : sur la page d'une offre, analyse du CV
  (gpt-4o-mini), entretien vocal en direct (gpt-live-1, micro necessaire) puis evaluation.
  La cle `OPENAI_API_KEY` doit etre dans `.env`.

## Pitch vocal (sprint 4)

Reponse modele a "Presentez-vous", faite a partir du CV (50 a 60 mots), ecrite par gpt-4o-mini et lue
par la voix Denise d'edge-tts (environ 4 s au total). Qualite des voix :
`python -m api_service.metriques_audio` compare sage (OpenAI), Denise (edge-tts) et VITS (Coqui TTS,
si installe) : WER et CER mesures automatiquement, MOS note a l'ecoute.
