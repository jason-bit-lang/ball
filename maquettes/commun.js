// Maquettes CVBoost : ce que base.html fera dans le vrai site (icones, en-tete, pied de page)
// et l'apparition des blocs au defilement.
const ICONES = `<svg width="0" height="0" style="position:absolute">
  <symbol id="i-depot" viewBox="0 0 24 24"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></symbol>
  <symbol id="i-cible" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/></symbol>
  <symbol id="i-micro" viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></symbol>
  <symbol id="i-loupe" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></symbol>
  <symbol id="i-note" viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></symbol>
  <symbol id="i-horloge" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></symbol>
  <symbol id="i-cadenas" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></symbol>
  <symbol id="i-bouclier" viewBox="0 0 24 24"><path d="M12 3l7 3v5c0 5-3.5 8-7 10-3.5-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></symbol>
  <symbol id="i-cle" viewBox="0 0 24 24"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3"/></symbol>
  <symbol id="i-actualise" viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/></symbol>
  <symbol id="i-maison" viewBox="0 0 24 24"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/></symbol>
  <symbol id="i-grille" viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/></symbol>
  <symbol id="i-personne" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.5 4.5-6 8-6s7 1.5 8 6"/></symbol>
  <symbol id="i-fleche" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>
  <symbol id="i-fichier" viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></symbol>
  <symbol id="i-oeil" viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></symbol>
  <symbol id="i-coche" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></symbol>
</svg>`;
document.body.insertAdjacentHTML('afterbegin', ICONES);

// Page active (attribut data-page de <body>) pour mettre le bon lien en surbrillance
const page = document.body.dataset.page;
const actif = nom => (nom === page ? 'actif' : '');
const lienBas = (nom, icone, texte, adresse) =>
  `<a href="${adresse}" class="${actif(nom)}"><svg class="icone"><use href="#i-${icone}"/></svg>${texte}</a>`;

document.body.insertAdjacentHTML('afterbegin', `
<header class="entete"><nav class="verre">
  <a class="logo" href="accueil.html"><span>CV<em>Boost</em></span></a>
  <div class="liens">
    <a class="${actif('accueil')}" href="accueil.html">Accueil</a>
    <a href="accueil.html#etapes">Comment ça marche</a>
    <a href="accueil.html#fonctions">Fonctionnalités</a>
  </div>
  <div class="menu">
    <a class="cache-mobile ${actif('inscription')}" href="inscription.html">Inscription</a>
    <a class="btn" href="connexion.html">Connexion</a>
  </div>
</nav></header>
<nav class="barre-bas verre">
  ${lienBas('accueil', 'maison', 'Accueil', 'accueil.html')}
  ${lienBas('fonctions', 'grille', 'Fonctions', 'accueil.html#fonctions')}
  ${lienBas('connexion', 'personne', 'Connexion', 'connexion.html')}
  ${lienBas('inscription', 'cle', 'Inscription', 'inscription.html')}
</nav>`);

document.body.insertAdjacentHTML('beforeend', `
<footer class="pied">
  <div class="pied-contenu verre">
    <div class="pied-marque">
      <a class="logo" href="accueil.html"><span>CV<em>Boost</em></span></a>
      <p>Votre prochaine opportunité prend vie ici.</p>
    </div>
    <div><h4>Découvrir</h4><a href="accueil.html#etapes">Comment ça marche</a><a href="accueil.html#fonctions">Fonctionnalités</a><a href="accueil.html#fonctions">Entretien vocal</a></div>
    <div><h4>Votre espace</h4><a href="connexion.html">Connexion</a><a href="inscription.html">Créer un compte</a><a href="#">Historique</a></div>
    <div><h4>Confiance</h4><span>CV traités en toute sécurité</span><span>Offres mises à jour chaque jour</span></div>
  </div>
  <div class="pied-bas"><span>© 2026 CVBoost</span><span>Projet capstone Kadea Academy</span></div>
</footer>`);

// Apparition des blocs quand ils entrent dans l'ecran
const observateur = new IntersectionObserver(entrees => {
  for (const entree of entrees) {
    if (entree.isIntersecting) { entree.target.classList.add('visible'); observateur.unobserve(entree.target); }
  }
}, { threshold: 0.2 });
document.querySelectorAll('.apparait, .final').forEach(bloc => observateur.observe(bloc));
