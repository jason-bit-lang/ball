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
- Ne jamais pousser `venv/`, `env/`, `__pycache__/`, les bases `database/*.db`, le dossier `uploads/` (ancien) ni les mp3 de `api_service/temp_audio/`.
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
- Commentaires (demande de l'apprenant, 29/10) : chaque fichier Python commence par son role dans le projet ;
  chaque fonction a une docstring qui dit ce qu'elle fait ET pourquoi ; un commentaire court avant chaque
  etape non evidente (le "pourquoi" plutot que le "quoi"). Fait pour les 21 fichiers Python le 29/10.
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
  - Extraction propre du texte du CV televerse (pypdf), garde dans la base depuis la partie 5.
  - Envoi du texte du CV et de l'offre ciblee a l'API OpenAI (gpt-4o-mini).
  - Le LLM joue le recruteur : resume du profil, pourcentage de compatibilite avec l'offre et
    premiere question d'entretien, le tout affiche sur l'interface.
  - Cle API lue avec python-dotenv (fichier `.env`), jamais ecrite dans le code.

Un premier travail existe mais doit etre revu et adapte.

Choix faits pendant la partie 3 :
- Tache du modele LoRA : description d'une offre -> "Poste : ... | Competences : ...".
  Jeu de donnees cree par `python -m ai_engine.prepare_dataset` (doublons exacts par SHA-256 et
  quasi-doublons retires, separation 80/10/10 par ordre d'empreinte, assertions anti-fuite).
- Dans flan-t5-small, les matrices `q_proj` et `v_proj` s'appellent `q` et `v` : ce sont elles qui
  sont ciblees par LoRA. Modele facebook/nllb-200 (depot module 3) ecarte : fait pour traduire,
  8 fois plus gros.
- Code du fine-tuning dans un vrai fichier Python, `ai_engine/train_lora.py` et `ai_engine/evaluate_model.py` (choix de
  l'apprenant) ; le notebook Colab ne fait que l'installer et le lancer. Bibliotheques dans
  `requirements-ia.txt`, separees de `requirements.txt` (le site n'utilise jamais PyTorch).
- Resultats LoRA (essai complet du 27/10 sur processeur, 20 epoques, 24 min ; ~5 min sur GPU Colab) :
  SacreBLEU test 3,0 sans LoRA -> 30,9 avec LoRA, 0,45 % des parametres entraines, adaptateur 1,4 Mo.
  `data/offres_ia.csv` (titre_ia, competences_ia, 116 offres) et `ai_engine/lora_cvboost/` sont dans
  le depot. Les competences produites par le modele sont filtrees (seulement les noms connus, sans
  doublon). Le matching donne le meme classement avec ou sans ces colonnes.
- Second entrainement (27/10, version en place) : competences cibles relues par gpt-4o-mini
  (`ai_engine/etiquettes_ia.py`, `data/competences_gpt.csv`), 118 offres (83/10/11). SacreBLEU test
  2,6 -> 35,3. Justesse des competences sur le test (F1 contre gpt-4o-mini) : 0,24 -> 0,35 ; les
  mots-cles du nettoyage restent a 0,49. mediacongo n'a pas d'archives (6 pages d'offres ouvertes).
  Un "avis d'infructuosite" est ensuite ajoute au filtre des annonces de resultats (117 offres).
- Table `Offre` dans la base du site, remplie au demarrage par `app_web/offres.py` (cle = url).
- Assistante DRH reactivee (`ASSISTANTE_ACTIVE = True` dans `app_web/routes.py`) apres un test avec la
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
  Limites : 5 entretiens vocaux par utilisateur sur 24 h (table `EntretienVocal`), 7 minutes
  par entretien (10 au depart ; 7 depuis le 30/10, choix de l'apprenant : DUREE_ENTRETIEN dans ia.py, consigne "environ
  5 questions" ; a 6:00 le navigateur envoie CONCLUSION pour que la recruteuse conclue, arret a 7:00). Voix : `sage` (VOIX dans `app_web/ia.py`), choisie par l'apprenant apres ecoute
  d'extraits gpt-4o-mini-tts de sage, cedar et marin.
- Deroulement : analyse ecrite du CV (gpt-4o-mini), entretien vocal, puis evaluation de la
  transcription (gpt-4o-mini). Paquet `openai==3.36.1` (version qui contient l'API Live).

### Partie 4 : Design

Claude propose plusieurs themes fluides et dynamiques ; l'apprenant choisit ou propose le sien.
Aucun emoji ni emoticone. Beau et sobre, sans exces.

TERMINEE le 28/10 : design integre au site, teste (69 tests Python + 78 tests navigateur) et
rapport PDF livre. Ce qui suit garde la trace des decisions prises avec l'apprenant.
Point de depart : l'apprenant veut plus qu'un changement de couleurs : chaque page belle, authentique et
dynamique, inspiree du style Liquid Glass d'Apple Music (iOS 27 : verre depoli, barre de navigation
flottante, pages d'artistes teintees par leur photo, icone noir et blanc, bleu pour l'element actif).
Proposition de Claude (adoptee) : fond d'ondes soyeuses, verre, barre flottante en bas
sur telephone, zone de depot du CV, niveau de correspondance en barre, page d'offre facon page
d'artiste, onde sonore reagissant a la voix pendant l'entretien, anneau pour la note. Captures et
videos dans le scratchpad (dossier design/).

Methode choisie : une maquette par page, captures et videos envoyees, puis integration dans le vrai
site. L'apprenant valide TOUT en une fois, a la fin, apres avoir choisi le theme (couleurs).
Les maquettes (dossier `maquettes/`, une page HTML par ecran) ont ete supprimees apres l'integration ;
elles restent dans l'historique git : `git checkout ac1322b -- maquettes`. Decisions pour l'accueil :
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
puissions l'analyser correctement." Dans tous les autres cas, des offres sont proposees.
Complement (demande de l'apprenant, 30/10) : l'analyseur ne lit QUE des CV. Un document qui n'a pas la forme d'un CV
(lettre, offre d'emploi, cours, rapport, facture...) est refuse avec "Ce document ne ressemble pas a un CV..." (voir partie 6). Regle des 10 s maintenue : pas d'attente artificielle (la
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
Proposition pour la page d'une offre (maquettes/offre.html) : en-tete facon page d'artiste (titre
centre, entreprise et lieu, pastilles niveau / publication / cloture, trois boutons ronds : Favori,
grand bouton mauve "Entretien vocal", Postuler) ; "Vous et ce poste" (atouts, a renforcer) ; annonce
decoupee en sections (titres numerotes en MAJUSCULES ou mots connus suivis de ":", puces "+ * >") et
repliee avec "Lire toute l'annonce" (31 offres sur 117 ont au moins 3 sections ; sinon, paragraphes
courts) ; assistante "Votre recruteuse" : analyse avec le bouton mauve et la bulle (comme l'envoi du
CV), entretien en direct facon lecteur (En direct, minuteur /10:00, onde qui suit la voix : bleue pour
la recruteuse, mauve pour le candidat, transcription en bulles, boutons Micro et Terminer rouge),
evaluation (anneau de la note, barres /10, reponses a retravailler repliables). Coeur : bulle
"Ajoutee a vos favoris - Voir l'historique". Offre close : pastille grise, Postuler grise, message
"vous pouvez toujours vous entrainer". Constat : beaucoup d'offres en base sont deja closes (ex. les
offres SODEICO du 20/10) : a l'integration, retirer les offres closes des resultats.
Bouton "Postuler" (accepte par l'apprenant ; PAS d'option "candidature envoyee") : il s'adapte a
l'annonce. Lien de candidature direct (62 offres sur 117) -> site de l'employeur dans un nouvel onglet
("Vous allez sur le site de l'employeur") ; adresse email trouvee dans le texte (33) -> "Postuler par
email" : panneau avec l'adresse, bouton Copier, rappel (CV, lettre, poste en objet) et "Ouvrir mon
application mail" (mailto avec l'objet "Candidature : <poste>") ; site cite dans le texte (3) -> ouvert
dans un nouvel onglet ; rien trouve (19) -> "Comment postuler" : panneau avec la section "Dossier de
candidature" de l'annonce et le lien vers l'annonce d'origine ; offre close -> bouton grise.
A l'integration : chercher email et site dans la description au nettoyage quand il n'y a pas de lien.
COULEURS CHOISIES (28/10) : palette "Lumiere" (fond gris tres clair, ondes bleues et jaunes, bleu
#0a6cff, mauve #7a5cff) en mode clair par defaut, et un MODE SOMBRE "Nuit de Kinshasa" que
l'utilisateur choisit lui-meme avec un bouton lune / soleil dans l'en-tete (pas de bascule automatique).
Le choix est retenu dans le navigateur (localStorage "theme"), applique dans le <head> avant
l'affichage (theme.js) pour eviter un flash blanc. Toutes les couleurs sont des variables dans
commun.css (:root et [data-theme="sombre"]) : --surface, --surface-douce, --piste, --trait,
--gris-doux, --vert, --jaune-texte, --rouge-texte, --onde-1/2/3 remplacent les blancs et gris ecrits en dur.
Bug corrige dans les maquettes : la classe "rond" servait deux fois (cercle d'attente renomme
"cercle-attente") ; .btn a maintenant border: none et font: inherit.

### Partie 5 : FastAPI, Docker et deploiement Render

- Orchestrateur FastAPI (`/speak-smart`) :
  1. Reformulation du CV brut en discours fluide via un prompt strict envoye a OpenAI.
  2. Envoi du texte a un modele vocal qui genere une presentation audio. En ligne : voix Denise
     d'`edge-tts` (fr-FR-DeniseNeural, gratuit, environ 1,5 s, mp3). Choix de l'apprenant le 29/10
     apres ecoute : la voix sage d'OpenAI (gpt-4o-mini-tts, environ 5 s) est abandonnee, sans voix
     de secours ; si edge-tts ne repond pas, un message clair s'affiche.
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

TERMINEE le 29/10 (rapport PDF de 13 pages livre). Repris du depot module 3 (tin-mzl) : le prompt du
pitch (coach professionnel, texte continu a la premiere personne, sans puces ni symboles, phrases
courtes pour la voix, ramene a 50-60 mots) et la suppression du mp3 temporaire apres l'envoi
(`BackgroundTasks` de FastAPI).

Decisions de l'apprenant (28/10) : le pitch sert de modele de reponse a "Presentez-vous" (premiere
question d'un entretien). Il est fait a partir du CV seulement (pas adapte a chaque offre).
Voix : d'abord sage, puis (29/10, apres ecoute des deux) Denise d'edge-tts seule.
Bouton "Ecouter mon pitch" dans le bandeau de la page des opportunites et sur les cartes "Mes CV".
L'apprenant a deja un compte Render. Render publie la BRANCHE DE TRAVAIL (claude/capstone-github-setup-g24r7p),
pas main (choix de l'apprenant : pas de fusion pour l'instant). GitHub Actions (deploy.yml) fait un
TEST DE DEMARRAGE avant chaque deploiement (aucun fichier de tests dans le depot) : construit l'image Docker,
lance site + API, verifie /health, l'accueil, l'inscription et l'envoi d'un petit CV Word, puis appelle le
Deploy Hook (secret GitHub RENDER_DEPLOY_HOOK ; sans ce secret, le deploiement est saute).
Fait (29/10) : app_web/config.py (ADRESSE_BASE, ADRESSE_API) ; Document.contenu et Document.texte ; api_service/
(pitch 50 a 60 mots, voix Denise d'edge-tts) ; route Flask
/pitch/<id> ; /health (site, base, api) ; pages erreur.html (404, 500) ; journal aussi dans la console ;
Dockerfile, .dockerignore, docker-compose.yml (db, api, web), demarrer.sh (Render : uvicorn 127.0.0.1:8000
+ gunicorn 1 processus 4 fils). Mesures : pitch 3,3 a 4,2 s avec Denise (6,4 a 7,5 s avec sage) ; image
184 Mo ; site + API 265 Mo de memoire. api_service/metriques_audio.py (resultats finaux, 5 pitchs, data/metriques_audio.csv) :
WER sage 4,2 %, Denise 6,1 %, VITS 7,3 % ; CER 1,7 %, 2,1 %, 2,0 % ; temps par extrait 4,1 s, 0,9 s, 1,1 s
(erreurs surtout sur les noms congolais) ; MOS a noter par l'apprenant (data/audio/notes_mos.csv).
Cookie de session Secure sur Render (variable RENDER).
EN LIGNE depuis le 29/10 : https://cvboost-kfyi.onrender.com (service "cvboost" srv-dbha4h0473hc739coqdg,
base "cvboost-db" dpg-dbha41u1egvs73evnfb0-a, Postgres 16 gratuit, expire le 28/11/2026, region frankfurt,
autoDeploy non). Premier deploiement en 2 min 30. Domaine cvboost-kfyi.onrender.com autorise dans l'environnement
(Playwright : chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } })). Test en ligne du 29/10 (Chromium, 15/15) :
/health 0,5 s, accueil 1 s, inscription 2,2 s, CV illisible refuse 3,5 s, envoi du CV -> 10 offres 5 s (dont 3 s
d'animation), pitch 5,3 s (60 mots, mp3 137 Ko), page d'offre 1,4 s, analyse DRH 5 s, connexion 2,2 s, email deja
utilise et mauvais mot de passe refuses, 404, aucune erreur JavaScript. En HTTPS, Flask-WTF exige l'en-tete Referer :
une requete POST sans Referer recoit 400 (normal, le navigateur l'envoie). Deux comptes test.render.*@example.com
crees dans la base en ligne pendant ce test. Entretien vocal WebRTC encore a tester dans un vrai navigateur.
Deploiement FAIT par Claude le 29/10 (session "Cvboost Render deployment") avec l'API Render
(https://api.render.com/v1, en-tete "Authorization: Bearer $RENDER_API_KEY", cle rangee par l'apprenant dans
les reglages de l'environnement, jamais dans la conversation) : service web "cvboost" (depot
https://github.com/jason-bit-lang/cvboost_enterprise, branche de travail, runtime docker, offre free, region
frankfurt, healthCheckPath /health, autoDeploy non) ; variables SECRET_KEY (generee, jamais affichee),
OPENAI_API_KEY, DATABASE_URL (adresse interne de cvboost-db). Les secrets GitHub ne peuvent pas etre ecrits
par Claude (aucun outil) et UptimeRobot demande le compte de l'apprenant : ces deux points lui reviennent.
MOS : 15 extraits anonymes a noter de 1 a 5 (sage, Denise, VITS), envoyes dans extraits_mos.zip ; les
regenerer avec python -m api_service.metriques_audio si besoin.

### Partie 6 : Tests, bugs et documentation

- Ecrire et executer des tests adaptes au projet, sans les ajouter au depot.
- Documenter les bugs trouves et proposer des corrections.
- Verifier que chaque fonctionnalite repond en moins de 10 secondes, meme avec une connexion lente.
- Rediger une documentation complete qui explique chaque partie et chaque etape de CVBoost.

Consignes de l'apprenant pour la documentation (29/10) : deux PDF, en francais, simples.
1. "Documentation du projet" : pour que l'apprenant explique CVBoost a d'autres ; globale, "comme un README pour
   humain" ; front-end survole ; back-end partie par partie (ce que fait la partie, comment on l'a faite, ce qu'elle
   cree, son impact sur les autres parties) ; une section "problemes rencontres et solutions".
2. "Explain Code (explication du code)" : l'architecture, le role de chaque dossier, puis chaque fichier Python :
   ce qu'il fait, ses fonctions, POURQUOI ce code et QUEL PROBLEME il resout ; surtout le back-end.
FAIT le 29/10 : CVBoost_documentation.pdf (17 pages) et CVBoost_explain_code.pdf (33 pages), envoyes a l'apprenant.
Sources dans le scratchpad, dossier doc6/ : documentation.html ; explain_1/2/3.html assembles en explain_code.html ;
commun.css ; pdf.js (PDF avec numero de page) ; espaces.py (espaces insecables avant ; : ? ! et dans les guillemets).
TESTS FAITS le 29/10 (demande de l'apprenant : tester toute l'application, attaques comprises ; RIEN corrige, on en
discute apres SES propres tests). Rapport : rapport6/CVBoost_rapport_partie6_tests.pdf (12 pages, envoye).
491 verifications, 484 reussies : site SQLite 120/122, Postgres 119/122 ; donnees + IA 76/76 (scraper en direct
compris) ; SacreBLEU recalcule 2,58 -> 35,14 ; vraie assistante 6/6 (CV piege 0 %, "donne-moi 100" -> 0/100) ; API du
pitch 18/19 ; Docker 12/12 (image sans .env/.git/base, utilisateur cvboost ; charge : 600 pages / 30 visiteurs, 0 erreur,
p95 945 ms, 352 Mo max sur 512) ; navigateur local 61/61 et en ligne 60/60 (32 affichages, liens, accessibilite, XSS,
redirections) ; en ligne 11/12. Regle des 10 s en 3G lente : tout passe (pitch 7,7 a 9,5 s), SAUF le reveil de Render
apres 15 min sans visite : 55,8 s. 27 attaques : 24 bloquees, 3 points faibles.
Bugs proposes (non corriges) : B1 nom de fichier > 255 caracteres -> erreur 500 sur Postgres ; B2 nom non latin
("简历.pdf") -> CV refuse (secure_filename efface l'extension) ; B3 corps > 5 Mo vers l'assistante traite comme un envoi
de CV (redirection + fausse ligne UPLOAD_REJECTED) ; B4 page 405 en anglais ; B5 message du pitch sans cle ("Reessayez") ;
B6 textes depasses (docstring metriques_audio, commentaire .gitignore). Code propose dans le rapport (section 5).
Ameliorations a decider : A1 UptimeRobot (reveil 55,8 s) ; A2 longueur du pitch 51 a 74 mots (max_tokens, coupe, pitch
garde en base) ; A3 pas de limite de tentatives de connexion ; A4 pas de limite sur analyse / evaluation / pitch (cout) ;
A5 pas d'en-tetes de securite (clickjacking) ; A6 CV sans rapport accepte des 1 mot commun ("do") ; A7 temps de
connexion revele si l'email existe ; A8 11 paires d'annonces a introduction commune dans data/ia ; A9 scraping sur main.
Tests dans le scratchpad, dossier p6test/ (test_site.py [postgres], test_donnees_ia.py [scraper], test_lora.py,
test_ia_reelle.py, test_api.py, charge.py, serveur_p6.py + navigateur_p6.js [enligne], resultats_*.json). Postgres de
test dans /tmp/pg6 (port 5433). Comptes crees en ligne : 4 test.render.p6.*@example.com (+ 2 de la partie 5), a
supprimer sur demande. Suite : l'apprenant teste lui-meme, puis discussion (ameliorer / laisser), puis peut-etre une
maquette de design qu'il donnera "juste pour un test".
Retour des tests de l'apprenant (30/10), CORRIGE le jour meme :
1. Apres la connexion, l'utilisateur ne reste plus sur l'accueil : page "Propulser votre CV" (/upload) s'il n'a encore
   aucun CV analyse (premiere fois), sinon son historique (/history) ; la page demandee avant la connexion (?next) reste
   prioritaire. Fonction page_d_arrivee() dans routes.py (aussi pour /login et /register ouverts deja connecte).
2. Seuls les CV sont acceptes : est_un_cv() dans matching.py. Indices = familles de rubriques trouvees en titre court
   (<= 5 mots : experience, formation, competences, langues, loisirs, references, profil, "Curriculum vitae", etat civil)
   + 1 si email ou telephone ; il en faut 3. Refus si 2 formules d'offre d'emploi ou plus ("date limite", "nous
   recherchons", "requis"...), sauf CV tres complet (6 indices : dossier lettre + CV). Message PAS_UN_CV, evenement
   PAS_UN_CV dans le journal. Mesure sur 345 documents (3 lots generes par gpt-4o-mini + 126 offres reelles + nos PDF) :
   111 CV sur 113 acceptes, 224 autres sur 232 refuses (passent : modeles de CV vides, biographies, brochure de formation).
   Le test de demarrage de deploy.yml envoie maintenant un petit CV avec rubriques. Tests : test_correctifs.py 41/41,
   navigateur_correctifs.js 14/14 (ordinateur + telephone), ancienne suite 119/122 (echecs attendus : CV jouet de 4 lignes
   refuse, lorem ipsum refuse avec le nouveau message, B2). Corpus dans le scratchpad, dossier cvtest/.
   Insistance de l'apprenant (30/10) : le "Propulser votre CV" n'accepte QUE des CV (ex. jamais un PDF bancaire).
   Ajoute donc un DEUXIEME CONTROLE : confirmer_cv() dans ia.py (gpt-4o-mini, QUESTION_CV, reponse JSON
   {"nature", "cv"}, temperature 0, DELAI_CV = 4 s). Appele seulement si la regle a accepte ; None si OpenAI ne repond
   pas (la regle decide seule). routes.py : `if not est_un_cv(texte) or confirmer_cv(texte) is False`. Mesure sur 389
   documents (lot v4 : releves bancaires, RIB, M-Pesa, bulletins de paie, fiche KYC, biographies, modeles vides) :
   263/263 non-CV refuses, 124/126 CV acceptes (regle seule : 247/263), environ 1 s. Tests : test_correctifs.py 69/69
   (vraie API, sans cle, panne, document piege), navigateur 14/14, ancienne suite 119/122 (memes echecs attendus).
   EN LIGNE depuis le 30/10 14 h 08 (commit c8d710c, publie par le DEPLOY HOOK, ajoute par l'apprenant vers 14 h 05 :
   chaque push sur la branche publie maintenant le site tout seul, apres le test de demarrage). Tests en ligne sur cette
   version : navigateur_correctifs.js enligne 14/14 ; enligne_banque.py : releve, RIB, attestation, M-Pesa, bulletin de
   paie, demande de pret, fiche KYC, biographie, modele de CV vide tous refuses, vrai CV accepte (1 s).
   Comptes de test ajoutes en ligne : test.render.p6.correctif.ordinateur/telephone.* (x2 passages) et
   test.render.p6.banque.* (x2, avec des documents de test), a supprimer sur demande.
   Documentation (19 pages) et Explain Code (36 pages) mis a jour le 30/10 avec ces deux problemes et leurs solutions
   (sources doc6/ ; copies d'avant dans doc6/*.avant30.html et doc6/ancien30/) ; l'apprenant gere la suite des PDF.
3. Entretien vocal de 7 minutes au lieu de 10 (demande de l'apprenant, 30/10) : voir partie 3. Teste avec une fausse
   recruteuse en WebRTC local (navigateur_duree.js + serveur_duree.py) : 11/11 (minuteur /07:00, "Environ 7 minutes",
   consigne de fin a 6:00 envoyee une seule fois, arret et evaluation a 7:00). Documentation et Explain Code mis a jour.
4. Entretien qui "crashait" sur l'iPhone de l'apprenant (30/10, journal Render) : a 14 h 31, session vocale creee (201)
   puis evaluation envoyee 1 s apres, VIDE -> 400 ; second essai sans suite. Cause exacte invisible depuis le serveur
   (liaison WebRTC du telephone ; impossible a reproduire ici : pas d'UDP). La recruteuse elle-meme fonctionne :
   entretien complet simule par WebSocket (scratchpad entretien/simulation.py, voix du candidat edge-tts) : salut,
   5 questions qui rebondissent, conclusion. Corrections : (a) consigne de fin envoyee en session.instructions.append
   (silencieuse ; en commentary la recruteuse disait "il nous reste une minute, finissez votre idee" et coupait la
   parole) ; ajoutee aux allowed_client_events ; (b) arret avant la premiere reponse : plus d'evaluation vide, message
   clair et relance sans recharger (recommencer() dans entretien.js) ; (c) chaque coupure est notee dans le journal :
   etape "incident" de la route entretien -> ENTRETIEN_INCIDENT (raison : session fermee par OpenAI + reason, liaison
   coupee ou impossible + etat, erreur OpenAI, erreur JavaScript, demarrage impossible) ; (d) AudioContext cree pendant
   le clic (sur iPhone, cree apres une attente il reste en pause : onde figee). Tests : navigateur_entretien2.js 12/12
   (iPhone 13 emule, fausse recruteuse WebRTC : coupure a 0,6 s, Terminer sans reponse, liaison impossible, entretien
   complet), navigateur_duree.js 11/11, route incident (connexion, propriete du CV, injection) OK, ancienne suite 119/122.
   A faire : quand l'apprenant refait un entretien sur iPhone, lire ENTRETIEN_INCIDENT dans le journal Render
   (scratchpad logs_render.py <debut> <fin> ENTRETIEN).

## Architecture du projet (imposee par la formation, mise en place le 29/10)

Depot GitHub renomme `cvboost_enterprise` le 29/10 (ancien nom `ball` : les anciens liens sont rediriges).
- `.github/workflows/` : `deploy.yml` (CI/CD Render) et `scraping.yml` (scraping quotidien).
- `app_web/` (sprint 1 et assistante DRH) : static/, templates/, models.py, routes.py, ia.py, config.py,
  et en plus __init__.py (cree le site), matching.py, affichage.py, journal.py, offres.py.
- `data_pipeline/` (sprint 2) : logs_parser.py (ancien audit_logs), scraper_jobs.py (scraper),
  pandas_cleaning.py (nettoyage_offres), et en plus kpi.py et config.py (chemins partages).
- `ai_engine/` (sprint 3) : prepare_dataset.py (dataset_ia), train_lora.py (entrainement seul),
  evaluate_model.py (SacreBLEU avec et sans LoRA + traitement par lot -> data/offres_ia.csv), et en plus
  etiquettes_ia.py, finetuning_lora.ipynb, lora_cvboost/ (adaptateur).
- `api_service/` (sprint 4) : main.py (/speak-smart, /health), services/llm_reformulator.py,
  services/tts_engine.py, temp_audio/ (mp3 supprimes apres l'envoi), et en plus metriques_audio.py.
  L'API n'importe pas app_web (charger le site doublerait la memoire) : elle lit DATABASE_URL elle-meme.
- `database/` : cvboost.db et analytics.db (crees automatiquement, jamais pousses).
- Racine : Dockerfile, docker-compose.yml, requirements.txt, .env.example, README.md, et en plus run.py,
  demarrer.sh, requirements-ia.txt, data/, CLAUDE.md. Les trois `__init__.py` sont gardes (accord de l'apprenant).
- `data/ia/*.jsonl` correspond a l'entrainement du 27/10 (118 offres) : ne pas le regenerer sans reentrainer
  (sinon une offre vue a l'entrainement pourrait passer dans le jeu de test).

## Acces et secrets

- GitHub : acces via l'application GitHub de Claude, jamais par mot de passe.
- Render : le deploiement passe par un Deploy Hook ou une cle API ajoutee par l'apprenant dans
  les secrets GitHub et les variables d'environnement Render.
- OpenAI : cle placee par l'apprenant dans `.env` (local) et dans les variables Render.
  Ne jamais la copier dans un fichier versionne ni dans un message.

## Verifications en attente cote apprenant (rappelees dans les rapports des parties 3, 4 et 5)

Avant la partie 6 (rapport de la partie 5, section 9, livre le 29/10) :
- FAIT le 30/10 : Deploy Hook de Render dans le secret GitHub RENDER_DEPLOY_HOOK (deploiement c8d710c verifie).
- Surveillance UptimeRobot de https://cvboost-kfyi.onrender.com/health toutes les 5 ou 10 minutes.
- Supprimer la cle d'API Render (Render et reglages de l'environnement) apres le Deploy Hook.
- Base Postgres gratuite : expire le 28/11/2026 (comptes et CV en ligne perdus ensuite).
- Sur le site en ligne (Chrome ou Edge) : entretien vocal, pitch (ordinateur et telephone), parcours complet clair/sombre,
  credit OpenAI.
- Sur le PC : git pull, supprimer les anciens dossiers vides (app, pipeline, api, modele, notebooks),
  pip install -r requirements.txt, python run.py + uvicorn api_service.main:app --port 8000.
- MOS : noter les 15 extraits (extraits_mos.zip envoye le 29/10, correspondance dans data/metriques_audio.csv).
- Facultatif : choisir la branche de travail comme branche par defaut sur GitHub (Settings > General), pour
  qu'un simple `git clone` la donne et que le scraping quotidien tourne dessus (voir "Branche unique").
- Facultatif : supprimer les comptes test.render.*@example.com de la base en ligne (sur demande).
- Toujours valables (parties 3 et 4) : cle OpenAI dans `.env` et credit OpenAI ; entretien vocal : entendre
  la recruteuse, etre compris, evaluation en moins de 10 s ; ancienne base `instance/cvboost.db` a deplacer
  dans `database/` ; notebook LoRA sur Colab facultatif (demonstration).

## Etat du projet et environnement de travail (mis a jour le 29/10)

- Partie 6 en cours : documentation, Explain Code et tests livres le 29/10 ; premiers retours de l'apprenant corriges le 30/10.
- Partie 5 terminee le 29/10 : site en ligne, rapport PDF livre (13 pages).
- Parties 1, 2, 3 et 4 terminees, rapports PDF livres (partie 2 : section 7 problemes/solutions ;
  partie 3 : sections 2 bis resultats LoRA, 3 assistante DRH, 4 bis problemes, 4 ter taille du code ;
  partie 4 : design page par page, code, tests, problemes et solutions).
- Fichiers du design (partie 4) : `app_web/templates/base.html` (en-tete, barre du bas, pied de page,
  theme), `macros.html` (icone, anneau), `icones.html` (icones SVG), une page par ecran ;
  `app_web/static/style.css` (12 sections, variables clair / sombre), `site.js` (commun), `envoi.js`
  (envoi du CV et bulle), `offre.js` (favori, Postuler, annonce), `entretien.js` (assistante DRH) ;
  `app_web/affichage.py` (dates en francais, echeance, annonce en sections, maniere de postuler) ;
  `run.py` ajoute les colonnes manquantes a une base existante.
- Les rapports (HTML sources + PDF) et les tests sont dans le dossier scratchpad de la session, pas dans
  le depot (le scratchpad peut disparaitre avec le conteneur : le code du depot fait foi).
  Rapports : rapport/CVBoost_rapport_partie1.pdf a partie5.pdf (+ rapport_partieN.html). Tests :
  test_partie1_v2.py, test_partie2_*.py, test_partie3.py, p4test/ (test_partie4.py, navigateur_partie4.js),
  serveur_p4.py, p5test/ (test_partie5.py, test_pitch.py, mesure_pitch.py, lancer_api.py, api.sh,
  navigateur_pitch.js, verifie_commentaires.py, lancer_metriques.py, captures_p5.js, smoke.py).
  Derniers resultats : 75/75 tests Python (SQLite), 72/72 sur Postgres, 78/78 navigateur, pitch 9/9.
  PDF generes depuis le HTML avec Playwright (page.pdf). Les tests de la partie 3 remplacent
  OpenAI par un faux client ; activer l'assistante a l'execution (rt.ASSISTANTE_ACTIVE = True).
- Environnements virtuels du scratchpad : app-venv (site + API), ia-venv (LoRA : torch CPU +
  requirements-ia), coqui-venv (VITS, `coqui-tts[codec]==0.28.0`).
- Environnement cloud : cles dans les variables `OPENAI_API_KEY` et `RENDER_API_KEY` (visibles seulement
  dans les sessions demarrees apres leur ajout). Domaines autorises ajoutes par l'apprenant : mediacongo.net,
  api.openai.com, huggingface.co, cdn-lfs.huggingface.co, cas-bridge.xethub.hf.co,
  cas-server.xethub.hf.co, us.aws.cdn.hf.co, download.pytorch.org, download-r2.pytorch.org,
  api.render.com, render.com, onrender.com, cvboost-kfyi.onrender.com (speech.platform.bing.com joignable).
- Outils du conteneur : Docker se lance avec `dockerd` (Docker Hub limite les telechargements : pour les
  tests, `mirror.gcr.io/library/postgres:16-alpine`) ; Postgres local dans /usr/lib/postgresql/16/bin ;
  edge-tts et Playwright doivent passer par le proxy (`HTTPS_PROXY`) dans le conteneur.
- Entrainement LoRA sur processeur : venv Python 3.12, `pip install torch --index-url
  https://download.pytorch.org/whl/cpu` (PyTorch de PyPI impose 2,5 Go de bibliotheques NVIDIA),
  puis `pip install -r requirements-ia.txt pandas==2.2.3`. Environ 25 min pour 20 epoques.
- Branche unique (decision de l'apprenant, 29/10) : `main` est abandonnee, seule la branche de travail
  `claude/capstone-github-setup-g24r7p` est utilisee (commits, clone, Render). Ne pas fusionner dans main.
  Raison : un `git clone` donnait main (version du 27/10, ancien design noir) chez un ami de l'apprenant.
  Le README indique `git clone -b claude/capstone-github-setup-g24r7p ...`. main recoit encore le scraping
  quotidien de l'ancien code (GitHub ne planifie que sur la branche par defaut).
- Demarrage sans `.env` (demande de l'apprenant, 29/10) : docker-compose.yml lit `.env` seulement s'il existe
  (`required: false`) et le site cree une SECRET_KEY temporaire au hasard si elle manque (avertissement dans le
  journal). Sans cle OpenAI, l'assistante DRH et le pitch affichent un message. `.env.example` reste versionne
  (choix de l'apprenant). Teste : docker compose sans .env, parcours navigateur 7/7, python run.py, 75/75 tests.

## Reprise apres /compact (demande de l'apprenant, 29/10)

1. Relire ce fichier en entier avant de repondre, pour etre de nouveau a la page.
2. Etat : parties 1 a 5 terminees, site en ligne (https://cvboost-kfyi.onrender.com), rapport de la partie 5
   livre. L'apprenant fait les verifications de la section "Verifications en attente cote apprenant".
3. Deploy Hook en place depuis le 30/10 : chaque push publie le site (verifier le deploiement sur Render apres un push).
4. Partie 6 : documentation, Explain Code et rapport de tests livres (voir la partie 6 ci-dessus). Premier retour de
   l'apprenant corrige le 30/10 (page d'arrivee apres connexion, refus des documents qui ne sont pas des CV). Suite :
   decider avec lui des corrections (B1 a B6) et ameliorations (A1 a A9) ; maquette ensuite.
