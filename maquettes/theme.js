// Mode clair ou sombre : applique le choix enregistre AVANT l'affichage de la page (pas de flash blanc).
// Dans le vrai site, ces lignes seront dans le <head> de base.html.
try {
  if (localStorage.getItem('theme') === 'sombre') document.documentElement.dataset.theme = 'sombre';
} catch (erreur) {
  // navigation privee : le choix n'est simplement pas memorise
}
