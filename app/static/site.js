// CVBoost : petits comportements communs a toutes les pages.
// Chaque bloc verifie d'abord que les elements existent sur la page affichee.

const jetonCsrf = document.querySelector('meta[name="csrf-token"]').content;

// Envoie une demande POST au serveur (avec le jeton anti-CSRF) et renvoie la reponse JSON
async function envoyerAuServeur(adresse, donnees = {}, delai = 12000) {
    const reponse = await fetch(adresse, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': jetonCsrf},
        body: JSON.stringify(donnees),
        signal: AbortSignal.timeout(delai),
    });
    const resultat = await reponse.json();
    if (!reponse.ok) throw new Error(resultat.erreur);
    return resultat;
}

// Bulle de confirmation en bas de l'ecran (favori ajoute, adresse copiee...)
function montrerToast(texte, lien) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = texte;
    if (lien) {
        const a = document.createElement('a');
        a.href = lien.adresse;
        a.textContent = lien.texte;
        toast.appendChild(a);
    }
    toast.classList.add('visible');
    clearTimeout(montrerToast.minuteur);
    montrerToast.minuteur = setTimeout(() => toast.classList.remove('visible'), 2600);
}

// 1. Bouton lune / soleil : change le mode et retient le choix dans le navigateur
document.getElementById('bouton-theme').addEventListener('click', () => {
    const sombre = document.documentElement.dataset.theme !== 'sombre';
    if (sombre) {
        document.documentElement.dataset.theme = 'sombre';
    } else {
        delete document.documentElement.dataset.theme;
    }
    try {
        localStorage.setItem('theme', sombre ? 'sombre' : 'clair');
    } catch (erreur) {
        // navigation privee : le choix vaut seulement pour cette page
    }
});

// 2. Apparition des blocs quand ils entrent dans l'ecran
const observateur = new IntersectionObserver(entrees => {
    for (const entree of entrees) {
        if (entree.isIntersecting) {
            entree.target.classList.add('visible');
            observateur.unobserve(entree.target);
        }
    }
}, {threshold: 0.2});
document.querySelectorAll('.apparait, .final').forEach(bloc => observateur.observe(bloc));

// 3. Formulaires de connexion et d'inscription
// Oeil : affiche ou masque le mot de passe
document.querySelectorAll('.voir').forEach(bouton => {
    bouton.addEventListener('click', () => {
        const champ = bouton.parentElement.querySelector('input');
        champ.type = champ.type === 'password' ? 'text' : 'password';
    });
});

// Solidite du mot de passe : trois barres qui se colorent (inscription)
const motDePasse = document.querySelector('.force') && document.getElementById('password');
if (motDePasse) {
    const COULEURS = ['var(--rouge-texte)', 'var(--accent-2)', 'var(--vert)'];
    const MOTS = ['Trop faible : 8 caractères minimum', 'Correct', 'Solide'];
    motDePasse.addEventListener('input', () => {
        const texte = motDePasse.value;
        let points = 0;
        if (texte.length >= 8) points++;
        if (/[0-9]/.test(texte) && /[a-zA-Z]/.test(texte)) points++;
        if (texte.length >= 10 && /[A-Z]/.test(texte)) points++;
        document.querySelectorAll('.force i').forEach((barre, i) => {
            barre.style.background = i < points ? COULEURS[points - 1] : '';
        });
        document.getElementById('indice-force').textContent = texte ? MOTS[Math.max(points, 1) - 1] : '';
    });

    // Confirmation : les deux mots de passe sont-ils identiques ?
    const confirmation = document.getElementById('confirmation');
    confirmation.addEventListener('input', () => {
        const indice = document.getElementById('indice-confirmation');
        const pareil = confirmation.value === motDePasse.value;
        indice.textContent = !confirmation.value ? '' : (pareil ? 'Les mots de passe correspondent' : 'Les mots de passe sont différents');
        indice.className = 'indice ' + (pareil ? 'bon' : 'mauvais');
    });
}

// Envoi d'un formulaire : le bouton tourne et se bloque (evite un double clic sur une connexion lente)
document.querySelectorAll('form .envoyer[data-attente]').forEach(bouton => {
    bouton.form.addEventListener('submit', () => {
        bouton.disabled = true;
        bouton.innerHTML = '<span class="cercle-attente"></span> ';
        bouton.append(bouton.dataset.attente);
    });
});

// 4. Page des opportunites : filtres par niveau
document.querySelectorAll('#filtres button').forEach(bouton => {
    bouton.addEventListener('click', () => {
        document.querySelectorAll('#filtres button').forEach(autre => autre.classList.toggle('actif', autre === bouton));
        document.querySelectorAll('.carte-offre').forEach(carte => {
            carte.hidden = bouton.dataset.niveau !== 'tous' && carte.dataset.niveau !== bouton.dataset.niveau;
        });
    });
});

// 5. Historique : onglets (la pilule glisse) et coeur pour retirer une offre des favoris
document.querySelectorAll('#onglets button').forEach(bouton => {
    bouton.addEventListener('click', () => {
        document.querySelectorAll('#onglets button').forEach(autre => autre.classList.toggle('actif', autre === bouton));
        document.getElementById('onglets').classList.toggle('droite', bouton.dataset.onglet === 'cv');
        document.getElementById('favoris').hidden = bouton.dataset.onglet !== 'favoris';
        document.getElementById('cv').hidden = bouton.dataset.onglet !== 'cv';
    });
});

document.querySelectorAll('.carte-favori .coeur').forEach(coeur => {
    coeur.addEventListener('click', async () => {
        try {
            await envoyerAuServeur(coeur.dataset.url);
            const carte = coeur.closest('.carte-favori');
            carte.style.opacity = 0;
            carte.style.transform = 'scale(.97)';
            setTimeout(() => carte.remove(), 300);
            const nombre = document.getElementById('nb-favoris');
            nombre.textContent = Number(nombre.textContent) - 1;
        } catch (erreur) {
            alert("La modification n'a pas pu être enregistrée. Réessayez.");
        }
    });
});
