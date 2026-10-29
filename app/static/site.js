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

function attendre(millisecondes) {
    return new Promise(fin => setTimeout(fin, millisecondes));
}

// Bouton mauve + bulle qui se remplit d'eau pendant "travail", puis bouton et bulle bleus quand c'est fini.
// Duree minimale de 3 s : l'eau a toujours le temps de monter. Sert a l'analyse de l'offre et au pitch.
async function avecBulle(bouton, bulle, texteEnCours, travail) {
    bouton.disabled = true;
    bouton.classList.add('en-cours');
    bouton.textContent = texteEnCours;
    bulle.hidden = false;
    setTimeout(() => bulle.classList.add('en-cours'), 50);
    const debut = Date.now();
    try {
        const resultat = await travail();
        await attendre(Math.max(0, 3000 - (Date.now() - debut)));
        bouton.classList.replace('en-cours', 'termine');
        bulle.classList.replace('en-cours', 'termine');
        return resultat;
    } catch (erreur) {
        bouton.classList.remove('en-cours');
        bulle.classList.remove('en-cours');
        bulle.hidden = true;
        bouton.disabled = false;
        throw erreur;
    }
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

// 6. Pitch vocal du CV : au premier clic, le serveur prepare le texte et la voix (environ 7 s),
// puis le lecteur audio s'affiche avec le texte du pitch
async function demanderPitch(adresse) {
    const reponse = await fetch(adresse, {method: 'POST', headers: {'X-CSRFToken': jetonCsrf},
                                          signal: AbortSignal.timeout(12000)});
    const type = reponse.headers.get('Content-Type') || '';
    if (!type.startsWith('audio/')) {
        const resultat = type.startsWith('application/json') ? await reponse.json() : {};
        throw new Error(resultat.erreur || 'Votre session a expiré : rechargez la page.');
    }
    // Le texte du pitch arrive dans un en-tete, avec les accents encodes
    return {son: await reponse.blob(), texte: decodeURIComponent(reponse.headers.get('X-Pitch-Texte') || '')};
}

document.querySelectorAll('.pitch').forEach(bloc => {
    const bouton = bloc.querySelector('button');
    const statut = bloc.querySelector('.statut');
    bouton.addEventListener('click', async () => {
        const texteBouton = bouton.innerHTML;
        statut.textContent = '';
        try {
            const pitch = await avecBulle(bouton, bloc.querySelector('.bulle'), 'Préparation du pitch',
                                          () => demanderPitch(bloc.dataset.url));
            bouton.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-coche"/></svg> Pitch prêt';
            await attendre(800);
            const lecteur = bloc.querySelector('.lecteur');
            const audio = lecteur.querySelector('audio');
            audio.src = URL.createObjectURL(pitch.son);
            lecteur.querySelector('.texte-pitch').textContent = pitch.texte;
            bloc.querySelector('.ligne-envoi').hidden = true;
            lecteur.hidden = false;
            audio.play().catch(() => {});  // si le navigateur bloque la lecture automatique, le bouton lecture reste la
        } catch (erreur) {
            bouton.innerHTML = texteBouton;
            statut.textContent = erreur.name === 'TimeoutError'
                ? 'Le pitch met trop de temps à arriver. Réessayez dans un instant.' : erreur.message;
        }
    });
});
