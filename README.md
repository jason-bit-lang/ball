<<<<<<< HEAD
[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/89Qc2aKD)
# CVBoost – MVP Web Platform

## 📌 Description du projet

**CVBoost** est une plateforme web développée avec **Flask** permettant aux utilisateurs de télécharger et gérer leurs CV afin d'obtenir, dans les prochaines phases du projet, des analyses intelligentes basées sur l'intelligence artificielle.

Cette première version correspond à un **MVP (Minimum Viable Product)** dont l'objectif est de poser les bases techniques de la plateforme :

* Gestion des utilisateurs (inscription / connexion)
* Upload sécurisé de CV
* Association des CV aux utilisateurs
* Historique des CV envoyés
* Simulation de l'interface d'analyse IA

Les fonctionnalités d'analyse et de matching d'offres seront intégrées dans les versions futures.

---

# 🧰 Technologies utilisées

| Composant            | Technologie           |
| -------------------- | --------------------- |
| Backend              | Python / Flask        |
| Authentification     | Flask-Login           |
| Hashage mot de passe | Werkzeug              |
| Base de données      | SQLite                |
| ORM                  | SQLAlchemy            |
| Frontend             | HTML5 / CSS3 / Jinja2 |
| UI Framework         | Bootstrap ou Tailwind |
| Sécurité fichiers    | UUID                  |

---

# 📁 Structure du projet

```
cvboost/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   │
│   ├── templates/
│   │   ├── index.html
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── upload.html
│   │   ├── history.html
│   │   └──

.html
│   │
│   ├── static/
│   │   ├── css/
│   │   └── js/
│
├── uploads/
│
├── instance/
│   └── cvboost.db
│
├── requirements.txt
├── run.py
└── README.md
```

---

# 👤 Fonctionnalités implémentées

## 1️⃣ Page d'accueil

Route : `/`

* Présentation du projet CVBoost
* Barre de navigation dynamique

  * Utilisateur anonyme : **Connexion / Inscription**
  * Utilisateur connecté : **Upload / Historique / Déconnexion**

---

## 2️⃣ Inscription utilisateur

Route : `/register`

Formulaire :

* Nom
* Prénom
* Email
* Mot de passe
* Confirmation du mot de passe

Fonctionnalités :

* Vérification unicité email
* Hash
=======
# cvboost
ihi
>>>>>>> 4ffa910cf1ee8c5bf499750b196881b902d66204
