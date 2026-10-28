// Maquettes CVBoost : petits comportements des formulaires de connexion et d'inscription

// 1. Oeil : affiche ou masque le mot de passe
document.querySelectorAll('.voir').forEach(bouton => {
  bouton.addEventListener('click', () => {
    const champ = bouton.parentElement.querySelector('input');
    champ.type = champ.type === 'password' ? 'text' : 'password';
  });
});

// 2. Solidite du mot de passe (inscription) : 3 barres qui se colorent
const motDePasse = document.querySelector('[name=password]');
const force = document.querySelector('.force');
function solidite(texte) {
  let points = 0;
  if (texte.length >= 8) points++;
  if (/[0-9]/.test(texte) && /[a-zA-Z]/.test(texte)) points++;
  if (texte.length >= 10 && /[A-Z]/.test(texte)) points++;
  return points;
}
if (force) {
  const couleurs = ['#c0392b', '#f2b705', '#1e7d4f'];
  const mots = ['Trop faible : 8 caractères minimum', 'Correct', 'Solide'];
  motDePasse.addEventListener('input', () => {
    const points = solidite(motDePasse.value);
    force.querySelectorAll('i').forEach((barre, i) => {
      barre.style.background = i < points ? couleurs[points - 1] : '';
    });
    document.getElementById('indice-force').textContent = motDePasse.value ? mots[Math.max(points, 1) - 1] : '';
  });
}

// 3. Confirmation (inscription) : les deux mots de passe sont-ils identiques ?
const confirmation = document.querySelector('[name=confirmation_mot_secret]');
if (confirmation) {
  confirmation.addEventListener('input', () => {
    const indice = document.getElementById('indice-confirmation');
    const pareil = confirmation.value === motDePasse.value;
    indice.textContent = confirmation.value ? (pareil ? 'Les mots de passe correspondent' : 'Les mots de passe sont différents') : '';
    indice.className = 'indice ' + (pareil ? 'bon' : 'mauvais');
  });
}

// 4. Envoi : le bouton tourne et se bloque pour eviter un double clic (utile si la connexion est lente)
document.querySelectorAll('form').forEach(formulaire => {
  formulaire.addEventListener('submit', evenement => {
    evenement.preventDefault();  // maquette uniquement : rien n'est envoye
    const bouton = formulaire.querySelector('.envoyer');
    bouton.disabled = true;
    bouton.innerHTML = '<span class="rond"></span> ' + bouton.dataset.attente;
  });
});
