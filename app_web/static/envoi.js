// Page d'envoi du CV : choix ou glisser-deposer du fichier, verification avant l'envoi,
// puis analyse : bouton mauve "Analyse en cours" et bulle qui se remplit, puis bleu "Analyse terminee"
// et arrivee sur la page des opportunites.
const TAILLE_MAX = 5 * 1024 * 1024;  // 5 Mo, comme sur le serveur
const DUREE_MIN = 3000;              // millisecondes : l'eau a toujours le temps de monter
const DELAI_MAX = 15000;             // millisecondes : au-dela, on previent l'utilisateur
const formulaire = document.getElementById('formulaire');
const champ = document.getElementById('cv');
const zone = document.getElementById('zone');
const carte = document.getElementById('fichier');
const bouton = document.getElementById('envoyer');
const bulle = document.getElementById('bulle');
const alerte = document.getElementById('alerte');
const TEXTE_BOUTON = bouton.innerHTML;
formulaire.noValidate = true;  // nos propres messages remplacent la bulle du navigateur

function afficherErreur(message) {
    alerte.textContent = message;
    alerte.hidden = false;
    formulaire.classList.remove('secoue');
    void formulaire.offsetWidth;  // relance l'animation si elle a deja eu lieu
    formulaire.classList.add('secoue');
}

function afficherFichier() {
    const fichier = champ.files[0];
    if (!fichier) return;
    const extension = fichier.name.split('.').pop().toLowerCase();
    if (extension !== 'pdf' && extension !== 'docx') {
        champ.value = '';
        afficherErreur('Seuls les fichiers PDF ou Word (.docx) sont acceptés.');
        return;
    }
    if (fichier.size > TAILLE_MAX) {
        champ.value = '';
        afficherErreur('Ce fichier dépasse 5 Mo. Enregistrez une version plus légère.');
        return;
    }
    alerte.hidden = true;
    document.getElementById('nom').textContent = fichier.name;
    document.getElementById('taille').textContent = fichier.size < 1024 * 1024
        ? Math.round(fichier.size / 1024) + ' Ko' : (fichier.size / 1024 / 1024).toFixed(1) + ' Mo';
    const type = document.getElementById('type');
    type.textContent = extension.toUpperCase();
    type.className = 'type-fichier ' + extension;
    zone.hidden = true;
    carte.hidden = false;
    // Sur un petit telephone, le bouton "Analyser mon CV" finissait sous la barre du bas : on l'amene a l'ecran
    document.getElementById('envoyer').scrollIntoView({behavior: 'smooth', block: 'center'});
}

champ.addEventListener('change', afficherFichier);
document.getElementById('changer').addEventListener('click', () => champ.click());

// Glisser-deposer : la zone s'illumine quand un fichier la survole
zone.addEventListener('dragover', evenement => {
    evenement.preventDefault();
    zone.classList.add('survol');
});
zone.addEventListener('dragleave', () => zone.classList.remove('survol'));
zone.addEventListener('drop', evenement => {
    evenement.preventDefault();
    zone.classList.remove('survol');
    champ.files = evenement.dataTransfer.files;
    afficherFichier();
});

// CV refuse (illisible, mauvais fichier, connexion coupee) : message et retour a la zone de depot
function analyseRatee(message) {
    bulle.hidden = true;
    bulle.classList.remove('en-cours');
    bouton.classList.remove('en-cours');
    bouton.disabled = false;
    bouton.innerHTML = TEXTE_BOUTON;
    champ.value = '';
    carte.hidden = true;
    zone.hidden = false;
    afficherErreur(message);
}

// Envoi du CV au serveur. Il repond { adresse: page des opportunites } ou { erreur: message }.
async function envoyerCv() {
    try {
        const reponse = await fetch(formulaire.action || location.href, {
            method: 'POST',
            headers: {'X-Requested-With': 'fetch'},
            body: new FormData(formulaire),  // contient le fichier et le jeton anti-CSRF
            signal: AbortSignal.timeout(DELAI_MAX),
        });
        return await reponse.json();
    } catch (erreur) {
        if (erreur.name === 'TimeoutError') return {erreur: 'La connexion est trop lente. Réessayez dans un instant.'};
        return {erreur: 'Erreur de connexion (ou session expirée). Rechargez la page et réessayez.'};
    }
}

formulaire.addEventListener('submit', async evenement => {
    evenement.preventDefault();
    if (!champ.files[0]) {
        afficherErreur("Choisissez d'abord votre CV (PDF ou Word).");
        return;
    }
    bouton.disabled = true;
    bouton.textContent = 'Analyse en cours';
    bouton.classList.add('en-cours');
    bulle.hidden = false;
    setTimeout(() => bulle.classList.add('en-cours'), 50);  // petit delai pour que la montee de l'eau soit animee

    const debut = Date.now();
    const reponse = await envoyerCv();
    const reste = Math.max(0, DUREE_MIN - (Date.now() - debut));
    setTimeout(() => {
        if (reponse.erreur) {
            analyseRatee(reponse.erreur);
            return;
        }
        bouton.classList.replace('en-cours', 'termine');
        bulle.classList.replace('en-cours', 'termine');
        bouton.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-coche"/></svg> Analyse terminée';
        setTimeout(() => { location.href = reponse.adresse; }, 1000);  // le temps de voir "Analyse terminee"
    }, reste);
});
