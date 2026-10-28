// Page d'une offre : favori (coeur), bouton Postuler, annonce repliee.

// 1. Favori : le coeur se remplit et une bulle confirme l'ajout a l'historique
const coeur = document.getElementById('favori');
coeur.addEventListener('click', async () => {
    try {
        const reponse = await envoyerAuServeur(coeur.dataset.url);
        coeur.classList.toggle('favori-actif', reponse.favori);
        coeur.setAttribute('aria-pressed', reponse.favori);
        if (reponse.favori) {
            montrerToast('Ajoutée à vos favoris', {adresse: coeur.dataset.historique, texte: "Voir l'historique"});
        } else {
            montrerToast('Retirée de vos favoris');
        }
    } catch (erreur) {
        montrerToast("Le favori n'a pas pu être enregistré. Réessayez.");
    }
});

// 2. Postuler : lien vers le site de l'employeur, ou panneau (email, comment postuler)
const postuler = document.getElementById('postuler');
const panneauPostuler = document.getElementById('panneau-postuler');
if (postuler && panneauPostuler) {
    postuler.addEventListener('click', () => { panneauPostuler.hidden = !panneauPostuler.hidden; });
    panneauPostuler.querySelector('.fermer').addEventListener('click', () => { panneauPostuler.hidden = true; });
} else if (postuler) {
    postuler.addEventListener('click', () => montrerToast("Vous allez sur le site de l'employeur..."));
}

const copier = document.getElementById('copier');
if (copier) {
    copier.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(copier.dataset.adresse);
            copier.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-coche"/></svg> Copiée';
        } catch (erreur) {
            montrerToast("Copie impossible : sélectionnez l'adresse à la main.");
        }
    });
}

// 3. Annonce : repliee si elle est longue, depliee avec "Lire toute l'annonce"
const annonce = document.getElementById('annonce');
const deplier = document.getElementById('deplier');
function toutAfficher() {
    annonce.classList.remove('repliee');
    deplier.hidden = true;
}
if (annonce.scrollHeight <= annonce.clientHeight + 40) toutAfficher();  // annonce courte : rien a replier
deplier.addEventListener('click', toutAfficher);
