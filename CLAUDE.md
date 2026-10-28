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
- Ne jamais pousser `venv/`, `env/`, `__pycache__/`, la base `database/*.db` ni le contenu de `uploads/`.
- La base SQLite locale est rangee dans le dossier `database/` (fichier `database/cvboost.db`),
  jamais dans `instance/` : ne pas utiliser le nom `instance` pour ce dossier.
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

Attentes de l'apprenant (a respecter dans toutes les parties) :
- Avancer partie par partie, sans se presser ; expliquer simplement, en francais.
- Code court et peu abondant : l'apprenant doit le comprendre et le maitriser entierement.
  Pas d'ecritures "astucieuses" (`**{...}`, `zip(*map(...))`, index croises...) : ecrire en clair.
- Chaque rapport PDF contient une section "Problemes rencontres et solutions" (probleme, cause,
  solution) et un rappel des verifications a faire cote apprenant.
- Prevenir l'apprenant a la fin des taches longues (scraping, entrainement, tests).

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
bloque ou interdit, proposer une source alternative.
Regle pour toute source d'offres : seules les offres accessibles a la population congolaise sont
gardees (postes bases en RDC, ouverts aux candidats nationaux). Pas d'offres internationales,
de teletravail pour l'etranger ou de postes reserves aux expatries.
Source unique retenue : mediacongo.net (annonces scannees lues par OCR, scraping quotidien via
GitHub Actions). ReliefWeb (API soumise a un nom d'application approuve) est mis de cote. Le scraping tourne a part (script ou tache
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
- Utilisation du modele LoRA sans surcharger Render : le modele tourne sur Colab en traitement
  par lot sur les offres scrapees (par exemple : description -> intitule et competences cles).
  Les resultats sont enregistres dans la base et le site les lit directement. En ligne, le
  matching CV/offres utilise ces donnees avec TF-IDF (scikit-learn), sans PyTorch.
  Option si le temps le permet : version ONNX quantifiee du modele chargee en ligne.
- Assistante DRH (module `ia.py`) :
  - Bouton "Simulation d'entretien" sur l'interface.
  - Extraction propre du texte du CV televerse (pypdf) depuis `uploads/`.
  - Envoi du texte du CV et de l'offre ciblee a l'API OpenAI (gpt-4o-mini).
  - Le LLM joue le recruteur : resume du profil, pourcentage de compatibilite avec l'offre et
    premiere question d'entretien, le tout affiche sur l'interface.
  - Cle API lue avec python-dotenv (fichier `.env`), jamais ecrite dans le code.

Un premier travail existe mais doit etre revu et adapte.

Choix faits pendant la partie 3 :
- Tache du modele LoRA : description d'une offre -> "Poste : ... | Competences : ...".
  Jeu de donnees cree par `python -m pipeline.dataset_ia` (doublons exacts par SHA-256 et
  quasi-doublons retires, separation 80/10/10 par ordre d'empreinte, assertions anti-fuite).
- Dans flan-t5-small, les matrices `q_proj` et `v_proj` s'appellent `q` et `v` : ce sont elles qui
  sont ciblees par LoRA. Modele facebook/nllb-200 (depot module 3) ecarte : fait pour traduire,
  8 fois plus gros.
- Code du fine-tuning dans un vrai fichier Python, `pipeline/finetuning_lora.py` (choix de
  l'apprenant) ; le notebook Colab ne fait que l'installer et le lancer. Bibliotheques dans
  `requirements-ia.txt`, separees de `requirements.txt` (le site n'utilise jamais PyTorch).
- Resultats LoRA (essai complet du 27/10 sur processeur, 20 epoques, 24 min ; ~5 min sur GPU Colab) :
  SacreBLEU test 3,0 sans LoRA -> 30,9 avec LoRA, 0,45 % des parametres entraines, adaptateur 1,4 Mo.
  `data/offres_ia.csv` (titre_ia, competences_ia, 116 offres) et `modele/lora_cvboost/` sont dans
  le depot. Les competences produites par le modele sont filtrees (seulement les noms connus, sans
  doublon). Le matching donne le meme classement avec ou sans ces colonnes.
- Second entrainement (27/10, version en place) : competences cibles relues par gpt-4o-mini
  (`pipeline/etiquettes_ia.py`, `data/competences_gpt.csv`), 118 offres (83/10/11). SacreBLEU test
  2,6 -> 35,3. Justesse des competences sur le test (F1 contre gpt-4o-mini) : 0,24 -> 0,35 ; les
  mots-cles du nettoyage restent a 0,49. mediacongo n'a pas d'archives (6 pages d'offres ouvertes).
  Un "avis d'infructuosite" est ensuite ajoute au filtre des annonces de resultats (117 offres).
- Table `Offre` dans la base du site, remplie au demarrage par `app/offres.py` (cle = url).
- Assistante DRH reactivee (`ASSISTANTE_ACTIVE = True` dans `app/routes.py`) apres un test avec la
  vraie API le 27/10 : analyse 6,4 s, creation de la session vocale 1 a 2 s, premier mot de la
  recruteuse 0,7 s apres le demarrage, evaluation 3,4 a 4,5 s. Le son WebRTC n'a pas pu etre teste
  depuis le conteneur cloud (pas d'UDP) : a valider dans un vrai navigateur (PC ou Render).
  Si la liaison audio echoue, un message clair s'affiche apres 7 s et l'utilisateur peut reessayer.
- Prompts de l'assistante inspires du projet IA_DRH (fourni par l'apprenant) : le recruteur prend
  l'initiative, pose une seule question a la fois, rebondit, demande role / methode / resultat,
  n'evalue pas pendant l'entretien ; a la fin, evaluation chiffree (note globale /100,
  communication, competences techniques et motivation /10, conseils par reponse, verdict).
  L'analyse ajoute les competences manquantes et des conseils pour ameliorer le CV.
- Choix de l'apprenant : entretien VOCAL EN DIRECT avec l'API Live d'OpenAI (`gpt-live-1`, WebRTC,
  environ 0,05 $ la minute hors modele de raisonnement, compte OpenAI payant ; l'apprenant paie).
  Le serveur cree seulement la session (le son passe directement entre le navigateur et OpenAI,
  Render n'est pas charge) ; le navigateur ne peut envoyer que l'accueil et le raccrochage.
  Limites : 5 entretiens vocaux par utilisateur sur 24 h (table `EntretienVocal`), 10 minutes
  par entretien. Voix : `sage` (VOIX dans `app/ia.py`), choisie par l'apprenant apres ecoute
  d'extraits gpt-4o-mini-tts de sage, cedar et marin.
- Deroulement : analyse ecrite du CV (gpt-4o-mini), entretien vocal, puis evaluation de la
  transcription (gpt-4o-mini). Paquet `openai==3.36.1` (version qui contient l'API Live).

### Partie 4 : Design

Claude propose plusieurs themes fluides et dynamiques ; l'apprenant choisit ou propose le sien.
Aucun emoji ni emoticone. Beau et sobre, sans exces.

En cours (28/10) : `style.css` reecrit avec des variables de couleur (theme A clair par defaut,
provisoire). L'apprenant veut plus qu'un changement de couleurs : chaque page belle, authentique et
dynamique, inspiree du style Liquid Glass d'Apple Music (iOS 27 : verre depoli, barre de navigation
flottante, pages d'artistes teintees par leur photo, icone noir et blanc, bleu pour l'element actif).
Proposition de Claude en attente de discussion : fond d'ondes soyeuses, verre, barre flottante en bas
sur telephone, zone de depot du CV, niveau de correspondance en barre, page d'offre facon page
d'artiste, onde sonore reagissant a la voix pendant l'entretien, anneau pour la note. Palettes
proposees : Sable et encre, Fleuve (clin d'oeil RDC), Nuit de Kinshasa. Les couleurs seront choisies
avec l'apprenant. Captures dans le scratchpad (dossier design/).

Methode choisie : une maquette par page, captures et videos envoyees, puis integration dans le vrai
site. L'apprenant valide TOUT en une fois, a la fin, apres avoir choisi le theme (couleurs).
Maquettes enregistrees dans le depot, dossier `maquettes/` (a ouvrir dans un navigateur) :
commun.css et commun.js (en-tete, pied de page, icones : ce que fera base.html), formulaire.js,
accueil.html, connexion.html, inscription.html, envoi.html, resultats.html, historique.html. A supprimer une fois le design integre au site. Decisions pour l'accueil :
- Titre : "Votre prochaine opportunite prend vie ici." ; bouton "Deposer mon CV" et
  "Sans engagement · 2 minutes · PDF ou Word" (ne jamais ecrire "gratuit").
- Demonstration animee en CSS (CV scanne -> competences -> offres avec niveau), sans compteur
  d'offres (il revele nos faiblesses) ni bandeau defilant.
- "Comment ca marche" en 3 etapes ; mosaique des fonctionnalites (entretien vocal avec onde
  decorative et bouton a cadenas qui mene a l'inscription, sans extrait de voix ; offres ; analyse ;
  note en anneau).
- Garanties : "Ouvert a tous, sans abonnement", "Vos CV traites en toute securite", "Des offres
  mises a jour chaque jour" (pas de mention des employeurs ni "seulement en RDC").
- Appel final : "Alors, pret a vous lancer vers votre prochaine opportunite ? Connectez-vous et
  deposez votre CV." mot par mot, "prochaine opportunite" en degrade.
- Pas de variante "Bon retour" sur l'accueil : le "Bon retour" va sur la page de connexion et le
  "Bienvenue" sur l'inscription.
- En-tete en verre flottant (nom "CVBoost" seul, sans logo dessine ; liens, boutons) ; sur telephone, barre flottante en bas
  avec icones. Vrai pied de page (Decouvrir, Votre espace, Confiance). Les deux dans base.html.
Propositions pour connexion et inscription (en attente de l'avis de l'apprenant) : mise en page en
deux colonnes (message a gauche, formulaire de verre a droite) ; connexion "Bon retour parmi nous."
avec trois cartes flottantes (offre, entretien vocal, note) ; inscription "Bienvenue sur CVBoost."
avec trois avantages coches qui arrivent l'un apres l'autre ; etiquettes flottantes dans les
champs, oeil pour voir le mot de passe, barre de solidite, verification de la confirmation, bouton
qui tourne pendant l'envoi, carte qui secoue en cas d'erreur. Message apres connexion :
"Bon retour, Prenom." Accepte par l'apprenant : connexion automatique apres l'inscription, puis
arrivee sur l'envoi du CV avec "Bienvenue sur CVBoost, Prenom."
Propositions pour l'envoi du CV (maquettes/envoi.html) : "Deposez votre CV." et 3 conseils pour un
CV bien lu (fichier cree sur ordinateur, competences en toutes lettres, experiences avec resultats) ;
zone de depot en pointilles qui defilent (glisser-deposer sur ordinateur, "Touchez pour choisir
votre CV" sur telephone) ; verification du type et des 5 Mo avant l'envoi ; carte du fichier
(PDF rouge, Word bleu, taille, "Pret a etre analyse", Changer) ; pendant l'envoi, faisceau de
l'accueil sur la carte et etapes (Envoi, Lecture, Recherche de vos competences). Sur telephone, la
zone passe avant les conseils. Messages flash en bulle de verre ; en-tete d'un utilisateur connecte :
Accueil, Propulser votre CV, Historique, Deconnexion (barre du bas : Accueil, Propulser, Historique,
Quitter).
Decisions de l'apprenant (28/10) : le lien du menu s'appelle "Propulser votre CV" (barre du bas :
"Propulser") ; la page garde le titre "Deposez votre CV." Au clic sur "Analyser mon CV", un ecran
d'analyse SANS TEXTE (choix de l'apprenant parmi 6 essais : "le liquide", une bulle de verre qui se
remplit d'eau avec deux vagues bleue et violette ; essais dans maquettes/analyse_essai*.html). Pas
d'ecran plein. Au clic : le bouton devient MAUVE et affiche "Analyse en cours", la petite bulle a cote
se remplit d'eau mauve ; quand le serveur a fini, la bulle se remplit jusqu'en haut et devient BLEUE, le
bouton devient bleu avec "Analyse terminee", puis la page des opportunites s'affiche (environ 1 s apres).
Integration : formulaire envoye avec fetch, duree minimale de 3 s pour que l'eau ait le temps de monter
(variable --mauve: #7a5cff). La page ne bouge pas, l'utilisateur attend simplement, puis l'utilisateur arrive directement sur une page dediee aux
resultats (l'ancienne page intermediaire "Mon CV" disparait du parcours). CV illisible, SI ET
SEULEMENT SI rien n'est reconnu dans le fichier (texte quasi vide comme un scan, moins de TEXTE_MIN = 200
caracteres, ou texte sans aucune competence ni aucun point commun avec les offres) : l'analyse
s'arrete, la zone de depot revient et le message s'affiche : "Nous n'avons pas pu analyser
correctement votre CV. Veuillez envoyer un autre CV, ou une autre version de votre CV, pour que nous
puissions l'analyser correctement." Dans tous les autres cas, des offres sont proposees. Regle des 10 s maintenue : pas d'attente artificielle (la
lecture du CV et le matching prennent environ 1 a 3 s).
Proposition pour la page des resultats (maquettes/resultats.html) : bandeau "Vos opportunites."
(Analyse terminee, nom du CV, date, competences reperees dans le CV en pastilles) ; filtres Toutes /
Tres proches / Proches / A explorer ; carte par offre avec jauge du niveau, entreprise, lieu, date
"Publiee le 7 octobre 2026", badge "Nouvelle" (moins de 7 jours), "Vos atouts" (competences en
commun) et "A renforcer" (competences de l'offre absentes du CV), boutons "Voir l'offre" et
"S'entrainer". Noms des competences a afficher joliment (comptabilite -> Comptabilite).
Regle de l'apprenant : la page des opportunites n'est jamais vide. S'il n'y a pas d'offre proche, on
propose quand meme les plus proches (niveau "A explorer") avec le message "Pas encore d'offre tres proche
de votre profil. Voici celles qui s'en rapprochent le plus..." (si aucune offre n'a de point commun avec
le CV, proposer les offres les plus recentes).
Historique (demande de l'apprenant, maquettes/historique.html) : "Votre historique." avec deux onglets
(pilule qui glisse) : "Offres favorites" et "Mes CV". On met une offre en favori depuis la page de
l'offre (bouton coeur) ; elle part dans l'historique. Carte d'un favori : coeur pour retirer, entreprise,
lieu, "Cloture le ..." avec badge ("19 jours restants" vert, "Plus que 3 jours" jaune, "Cloturee" gris,
"Date limite non precisee") et barre du temps ecoule, dernier entretien (note en anneau) et boutons
"Lancer l'entretien" (mauve) / "Voir l'offre". Carte d'un CV : type, nom, date, competences reperees,
"Voir mes opportunites". Etat vide avec invitation. A faire a l'integration : table Favori (user_id,
offre_id, date), route pour ajouter/retirer, et colonne date_limite extraite des descriptions dans le
nettoyage (premier essai : 58 offres sur 117 avec une date lisible, "au plus tard le", "Date limite",
"cloture"...). Les notes d'entretien viennent de l'evaluation (a enregistrer en base).

### Partie 5 : FastAPI, Docker et deploiement Render

- Orchestrateur FastAPI (`/speak-smart`) :
  1. Reformulation du CV brut en discours fluide via un prompt strict envoye a OpenAI.
  2. Envoi du texte a un modele vocal qui genere une presentation audio. En ligne : OpenAI
     `gpt-4o-mini-tts` (choix de l'apprenant, environ 7 s, quelques centimes), avec un delai
     maximum de 7 s. En cas d'erreur, de delai depasse ou de credit epuise, bascule automatique
     sur `edge-tts` (gratuit, environ 2 s, sortie mp3) pour rester sous les 10 s au total.
     Pitch court (environ 60 mots) pour limiter le temps de generation.
     Coqui TTS / VITS est garde pour la demonstration en local ou sur Colab et pour mesurer
     WER, CER et MOS.
- Connexion entre l'application Flask et FastAPI : une route Flask appelle FastAPI pour recuperer
  les echanges ; FastAPI lit les CV references dans la base de donnees. L'application Flask est
  reliee a tout : l'assistante DRH, le resume et la synthese vocale.
- Docker : Dockerfile optimise et `docker-compose.yml` qui separe les services web, API et base
  de donnees.
- CI/CD : pipeline GitHub Actions qui teste puis deploie automatiquement sur Render (via un
  Deploy Hook stocke dans les secrets GitHub).
- MLOps : route de sante, journalisation des erreurs, documentation des metriques audio
  (WER, CER, MOS).

Hebergement gratuit sur Render (offre Free : environ 512 Mo de RAM, mise en veille apres
15 minutes, disque efface au redemarrage, 750 heures par mois) :
- Pas de PyTorch en ligne : ni Coqui TTS ni modele LoRA charges sur Render.
- Un seul service Render qui fait tourner Flask et FastAPI ensemble. En local, docker-compose
  separe les services web, API et base de donnees.
- Base de donnees : Postgres gratuit de Render (expire apres 30 jours, suffisant pour le
  projet), adresse lue depuis la variable `DATABASE_URL`. SQLite reste utilise en local.
- Les CV sont enregistres dans la base de donnees (5 Mo maximum), pas sur le disque.
- Une route `/health` est appelee toutes les 10 minutes par UptimeRobot ou cron-job.org pour
  garder le site eveille et respecter la limite des 10 secondes.

Rien n'existe encore pour cette partie. A reprendre du depot module 3 (tin-mzl) : le prompt du pitch
(coach professionnel, texte continu a la premiere personne, sans puces ni symboles, phrases courtes
pour la voix ; ramener a environ 60 mots) et la suppression du fichier audio temporaire apres
l'envoi (`BackgroundTasks` de FastAPI).

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

## Verifications en attente cote apprenant (rappelees dans le rapport de la partie 3)

- Deplacer `instance/cvboost.db` vers `database/`, puis `pip install -r requirements.txt`.
- Cle OpenAI dans `.env` et credit sur le compte OpenAI.
- Entretien vocal dans un vrai navigateur (Chrome ou Edge) : entendre la recruteuse, etre compris,
  evaluation affichee en moins de 10 s.
- Notebook LoRA sur Colab : facultatif (l'essai complet est deja fait), utile pour la demonstration.

## Etat du projet et environnement de travail (mis a jour le 27/10)

- Parties 1, 2 et 3 terminees, rapports PDF livres (partie 2 : section 7 problemes/solutions ;
  partie 3 : sections 2 bis resultats LoRA, 3 assistante DRH, 4 bis problemes, 4 ter taille du code).
  Prochaine etape : partie 4 (design : proposer 2 ou 3 themes, l'apprenant choisit), puis 5 et 6.
  A corriger en partie 4 : description des offres en un seul bloc, dates au format 2026-10-07,
  scores TF-IDF peu parlants (afficher un niveau), phrase sur l'envoi des donnees a OpenAI.
- Les rapports (HTML sources + PDF) et les tests (test_partie1_v2.py, test_partie2_*.py,
  test_partie3.py, navigateur *.js) sont dans le dossier scratchpad de la session, pas dans le
  depot. PDF generes depuis le HTML avec Playwright (page.pdf). Les tests de la partie 3 remplacent
  OpenAI par un faux client ; activer l'assistante a l'execution (rt.ASSISTANTE_ACTIVE = True).
- Environnement cloud : cle OpenAI dans la variable `OPENAI_API_KEY` (visible seulement dans les
  sessions demarrees apres son ajout). Domaines autorises ajoutes par l'apprenant : mediacongo.net,
  api.openai.com, huggingface.co, cdn-lfs.huggingface.co, cas-bridge.xethub.hf.co,
  cas-server.xethub.hf.co, us.aws.cdn.hf.co, download.pytorch.org, download-r2.pytorch.org.
- Entrainement LoRA sur processeur : venv Python 3.12, `pip install torch --index-url
  https://download.pytorch.org/whl/cpu` (PyTorch de PyPI impose 2,5 Go de bibliotheques NVIDIA),
  puis `pip install -r requirements-ia.txt pandas==2.2.3`. Environ 25 min pour 20 epoques.
- Le workflow de scraping quotidien n'est actif qu'une fois la branche fusionnee dans `main`
  (pas de pull request sans demande de l'apprenant).
