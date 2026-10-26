# CVBoost

## Le projet

CVBoost est un site web qui aide les utilisateurs a trouver du travail. L'utilisateur s'inscrit,
se connecte puis televerse son CV. L'IA integree (modele fine-tune avec LoRA) lit le PDF et cherche
les offres d'emploi qui correspondent au contenu du CV. L'utilisateur choisit une offre, puis peut
simuler un entretien avec l'assistante DRH (IA) affichee a cote. L'assistante pose des questions
basees sur l'offre et sur le CV.

Des que le CV est televerse, les deux IA (moteur de matching et assistante DRH) le recoivent et
l'analysent. Quand l'utilisateur clique sur "Rechercher", le moteur propose les offres adaptees
(un developpeur recoit des offres de developpeur). En ouvrant une offre, l'assistante DRH apparait
et peut lui faire passer un entretien sur ce poste.

## Regles de code (obligatoires)

- Code court, clair et comprehensible pour un debutant en developpement web.
- Code DRY : pas de duplication, factoriser ce qui se repete.
- Commentaires clairs et directs, sans emojis ni emoticones.
- Le projet sera deploye : il doit fonctionner pour tout le monde dans un navigateur, sans bug,
  et pas seulement en local.
- Aucun secret dans le depot : la cle OpenAI, la SECRET_KEY et les acces sont lus depuis `.env`
  (python-dotenv) en local et depuis les variables d'environnement sur Render. `.env` est dans
  `.gitignore` ; seul `.env.example` (sans vraies valeurs) est versionne.
- Ne jamais pousser `venv/`, `env/`, `__pycache__/`, la base `instance/*.db` ni le contenu de `uploads/`.
- Toute fonctionnalite doit repondre en moins de 10 secondes, meme avec une connexion lente :
  prevoir des timeouts et un message d'erreur clair cote utilisateur.

## Objectif final

Livrer l'architecture complete de CVBoost : plateforme web securisee, pipeline de donnees,
moteur d'IA local fine-tune avec LoRA, assistante DRH qui evalue les profils, orchestrateur audio
(FastAPI + synthese vocale) et deploiement Cloud automatise (Docker, GitHub Actions, Render).

A la fin, l'apprenant doit comprendre :

1. Developpement web et securite : application Flask, authentification securisee, stockage
   persistant des documents.
2. Data engineering et analytics : pipeline ETL (logs, web scraping, SQL analytique, Pandas).
3. NLP et fine-tuning open source : jeux de donnees sans fuite, fine-tuning LoRA/PEFT,
   evaluation SacreBLEU.
4. Extraction et prompt engineering (IA DRH) : extraction du texte d'un PDF (pypdf) et
   interrogation d'un LLM (OpenAI) pour evaluer un candidat.
5. Architecture hybride et multimodale : API FastAPI combinant LLM et synthese vocale (Coqui TTS)
   pour generer un pitch audio du candidat.
6. MLOps, conteneurisation et Cloud : Docker, deploiement GitHub Actions vers Render, supervision
   en production.

Pour chacun de ces 6 points, Claude fournit une explication et un PDF qui explique les parties
du code correspondantes.

## Methode de travail

Le projet se fait en 6 parties. Pour chaque partie : analyser, comprendre, agir, puis verifier que
tout fonctionne sans bug. A la fin de chaque partie, Claude livre un rapport PDF : ce qui a ete
fait, ce qui fonctionne, ce qui ne fonctionne pas encore. Delai total : 3 jours.

### Partie 1 : Utilisateurs et interfaces

- Application Flask et authentification : inscription, connexion securisee (hashage Werkzeug,
  Flask-Login), gestion des sessions.
- Persistance et fichiers : tables User et Document (SQLAlchemy). Televersement securise du CV
  (PDF/DOCX, 5 Mo maximum, renommage UUID).
- Interface : templates Jinja2 avec composants reutilisables (base.html), navigation dynamique,
  page historique de l'utilisateur.

Cette partie existe deja mais contient des erreurs. A faire :
- Tester l'inscription et la connexion, des mots de passe errones sur 2 comptes differents,
  l'inscription avec un email deja utilise et la navigation entre les pages.
- Lister les bugs et proposer les corrections.
- Noter les ameliorations d'interface possibles (appliquees plus tard, dans la partie Design).
- Compte de test de l'application (local uniquement, pas un compte GitHub) :
  `jasonnzanda3@gmail.com` / `Jason123`.

### Partie 2 : Donnees (essentielle pour la suite)

- Audit et logs : script qui lit les logs de televersement, detecte les tentatives de fraude et
  extrait les metadonnees.
- Base analytique SQL : base dediee aux KPI (`analytics.db`, SQLite ou PostgreSQL), statistiques
  d'usage avec requetes avancees (GROUP BY, HAVING).
- Collecteur d'offres (web scraping) : robot BeautifulSoup qui recupere des offres reelles
  (intitule, entreprise, description, salaire) en respectant la courtoisie web (User-Agent, delais).
- Nettoyage et normalisation (Pandas) : doublons, valeurs manquantes, conversion des salaires,
  encodage des competences pour rendre le dataset utilisable par l'IA.

Source : mediacongo.net. Verifier d'abord son `robots.txt` et ses conditions ; si le scraping est
bloque ou interdit, proposer une source alternative. Le scraping tourne a part (script ou tache
planifiee) et ne doit jamais ralentir le site. Les offres collectees servent aux parties suivantes.
Un premier travail existe : l'adapter a ces instructions.

### Partie 3 : IA DRH, moteur NLP et fine-tuning

- Pipeline anti-fuite (Hugging Face) : deduplication par hash SHA-256, separation stricte
  80 % train / 10 % validation / 10 % test, verifiee par des assertions automatiques.
- Fine-tuning LoRA/PEFT : poids d'origine geles, matrices ciblees `q_proj` et `v_proj`.
  Modele propose : un petit modele seq2seq (par exemple flan-t5-small) pour rester compatible
  avec Seq2SeqTrainer et SacreBLEU et tenir dans le delai. L'entrainement se fait sur GPU
  (Google Colab) ; seul l'adaptateur LoRA est ajoute au projet.
- Evaluation : score SacreBLEU sur le jeu de test via Seq2SeqTrainer.
- Assistante DRH (module `ia.py`) :
  - Bouton "Simulation d'entretien" sur l'interface.
  - Extraction propre du texte du CV televerse (pypdf) depuis `uploads/`.
  - Envoi du texte du CV et de l'offre ciblee a l'API OpenAI (gpt-4o-mini).
  - Le LLM joue le recruteur : resume du profil, pourcentage de compatibilite avec l'offre et
    premiere question d'entretien, le tout affiche sur l'interface.
  - Cle API lue avec python-dotenv (fichier `.env`), jamais ecrite dans le code.

Un premier travail existe mais doit etre revu et adapte.

### Partie 4 : Design

Claude propose plusieurs themes fluides et dynamiques ; l'apprenant choisit ou propose le sien.
Aucun emoji ni emoticone. Beau et sobre, sans exces.

### Partie 5 : FastAPI, Docker et deploiement Render

- Orchestrateur FastAPI (`/speak-smart`) :
  1. Reformulation du CV brut en discours fluide via un prompt strict envoye a OpenAI.
  2. Envoi du texte a un modele vocal (Coqui TTS / VITS) qui genere une presentation `.wav`.
- Connexion entre l'application Flask et FastAPI : une route Flask appelle FastAPI pour recuperer
  les echanges ; FastAPI lit les CV references dans la base de donnees. L'application Flask est
  reliee a tout : l'assistante DRH, le resume et la synthese vocale.
- Docker : Dockerfile optimise et `docker-compose.yml` qui separe les services web, API et base
  de donnees.
- CI/CD : pipeline GitHub Actions qui teste puis deploie automatiquement sur Render (via un
  Deploy Hook stocke dans les secrets GitHub).
- MLOps : route de sante, journalisation des erreurs, documentation des metriques audio
  (WER, CER, MOS).

Attention : l'offre gratuite de Render (512 Mo de RAM) ne suffit pas pour Coqui TTS. Prevoir un
plan payant ou une solution de synthese vocale plus legere en secours, pour respecter la limite
des 10 secondes.

Rien n'existe encore pour cette partie.

### Partie 6 : Tests, bugs et documentation

- Ecrire et executer des tests adaptes au projet, sans les ajouter au depot.
- Documenter les bugs trouves et proposer des corrections.
- Verifier que chaque fonctionnalite repond en moins de 10 secondes, meme avec une connexion lente.
- Rediger une documentation complete qui explique chaque partie et chaque etape de CVBoost.

## Acces et secrets

- GitHub : acces via l'application GitHub de Claude, jamais par mot de passe.
- Render : le deploiement passe par un Deploy Hook ou une cle API ajoutee par l'apprenant dans
  les secrets GitHub et les variables d'environnement Render.
- OpenAI : cle placee par l'apprenant dans `.env` (local) et dans les variables Render.
  Ne jamais la copier dans un fichier versionne ni dans un message.
