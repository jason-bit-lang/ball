// Assistante DRH : analyse du CV, entretien vocal en direct (gpt-live-1 via WebRTC) puis evaluation.
// Le son passe directement entre le navigateur et OpenAI ; Flask cree seulement la session.
const panneau = document.getElementById('entretien');
const statut = document.getElementById('statut');
const DELAI_MAX = 12000;      // millisecondes : au-dela, on previent l'utilisateur
const DUREE_MAX = 10 * 60;    // secondes : l'entretien s'arrete tout seul (il est paye a la minute)
const SILENCE = 1500;         // millisecondes sans parole de la recruteuse : c'est au candidat de parler
const CONNEXION_MAX = 7000;   // millisecondes pour etablir la liaison audio (total sous 10 s)
const ERREUR_AUDIO = "La liaison audio n'a pas pu s'établir (réseau ou pare-feu). Réessayez sur une autre connexion.";

const direct = {connexion: null, canal: null, micro: null, son: null, messages: [], debut: 0,
                minuteur: null, dernierePhrase: 0, accueil: '', fini: false, attente: null};

const $ = id => document.getElementById(id);

// Envoie une etape (analyse, vocal, evaluation) a Flask et renvoie la reponse JSON
async function appeler(etape, donnees = {}) {
    // data-url se termine par /analyse : on remplace ce dernier mot par l'etape voulue
    const reponse = await fetch(panneau.dataset.url.replace(/[^/]+$/, etape), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
        },
        body: JSON.stringify(donnees),
        signal: AbortSignal.timeout(DELAI_MAX),
    });
    const resultat = await reponse.json();
    if (!reponse.ok) throw new Error(resultat.erreur);
    return resultat;
}

function messageErreur(erreur) {
    if (erreur.name === 'TimeoutError') return "L'assistante met trop de temps à répondre. Réessayez.";
    if (erreur.name === 'NotAllowedError') return "Autorisez l'accès au micro pour passer l'entretien.";
    return erreur.message || 'Erreur de connexion. Réessayez.';
}

// textContent : le texte n'est jamais interprete comme du HTML
function remplirListe(id, elements) {
    elements.forEach(texte => {
        const ligne = document.createElement('li');
        ligne.textContent = texte;
        $(id).appendChild(ligne);
    });
}

// ---------- 1. Analyse ecrite du CV ----------
$('analyser').addEventListener('click', async event => {
    event.target.disabled = true;
    statut.textContent = "L'assistante lit votre CV...";
    try {
        const analyse = await appeler('analyse');
        $('score').textContent = analyse.compatibilite;
        $('resume').textContent = analyse.resume;
        ['points_forts', 'points_a_ameliorer', 'competences_manquantes', 'recommandations'].forEach((cle, i) =>
            remplirListe(['forts', 'faibles', 'manquantes', 'recommandations'][i], analyse[cle]));
        $('analyse').hidden = false;
        event.target.hidden = true;
        statut.textContent = '';
    } catch (erreur) {
        statut.textContent = messageErreur(erreur);
        event.target.disabled = false;
    }
});

// ---------- 2. Entretien vocal en direct ----------
$('demarrer').addEventListener('click', async event => {
    event.target.disabled = true;
    statut.textContent = "Préparation de l'entretien...";
    try {
        direct.micro = await navigator.mediaDevices.getUserMedia({audio: true});
        direct.connexion = new RTCPeerConnection();
        direct.son = new Audio();
        direct.son.autoplay = true;
        direct.connexion.ontrack = e => { direct.son.srcObject = e.streams[0]; };
        direct.connexion.addTrack(direct.micro.getAudioTracks()[0], direct.micro);
        direct.canal = direct.connexion.createDataChannel('oai-events');
        direct.canal.addEventListener('message', e => recevoir(JSON.parse(e.data)));
        direct.connexion.addEventListener('connectionstatechange', () => {
            if (direct.connexion.connectionState === 'failed') echecAudio();
        });

        const offre = await direct.connexion.createOffer();
        await direct.connexion.setLocalDescription(offre);
        const session = await appeler('vocal', {sdp: offre.sdp});
        direct.accueil = session.accueil;
        await direct.connexion.setRemoteDescription({type: 'answer', sdp: session.sdp});
        // Sans session.started dans le delai, la liaison audio est consideree comme bloquee
        direct.attente = setTimeout(echecAudio, CONNEXION_MAX);
        event.target.hidden = true;
        $('direct').hidden = false;
        statut.textContent = '';
    } catch (erreur) {
        fermerConnexion();
        statut.textContent = messageErreur(erreur);
        event.target.disabled = false;
    }
});

function envoyer(evenement) {
    if (direct.canal && direct.canal.readyState === 'open') direct.canal.send(JSON.stringify(evenement));
}

// Evenements envoyes par OpenAI sur le canal de donnees
function recevoir(evenement) {
    if (evenement.type === 'session.started') {
        clearTimeout(direct.attente);
        // C'est la recruteuse qui ouvre l'entretien
        envoyer({type: 'session.commentary.append', delegation_id: null, content: direct.accueil});
        direct.debut = Date.now();
        direct.minuteur = setInterval(chaqueSeconde, 1000);
        $('etat').textContent = 'La recruteuse arrive...';
    } else if (evenement.type === 'session.output_transcript.delta') {
        direct.dernierePhrase = Date.now();
        ajouterTexte('recruteur', evenement.delta);
    } else if (evenement.type === 'session.input_transcript.delta') {
        ajouterTexte('candidat', evenement.delta);
    } else if (evenement.type === 'session.closed') {
        terminer();  // session coupee ou expiree
    }
}

// Les fragments de texte arrivent mot par mot : on les regroupe par personne qui parle
function ajouterTexte(role, fragment) {
    let dernier = direct.messages[direct.messages.length - 1];
    if (!dernier || dernier.role !== role) {
        const bulle = document.createElement('p');
        bulle.className = 'bulle ' + (role === 'recruteur' ? 'assistante' : 'candidat');
        $('conversation').appendChild(bulle);
        dernier = {role: role, texte: '', bulle: bulle};
        direct.messages.push(dernier);
    }
    dernier.texte += fragment;
    dernier.bulle.textContent = dernier.texte;
}

function chaqueSeconde() {
    const secondes = Math.floor((Date.now() - direct.debut) / 1000);
    $('minuteur').textContent = String(Math.floor(secondes / 60)).padStart(2, '0') + ':' +
                                String(secondes % 60).padStart(2, '0');
    if (direct.dernierePhrase) {
        $('etat').textContent = Date.now() - direct.dernierePhrase < SILENCE ? 'La recruteuse parle...'
            : (direct.micro.getAudioTracks()[0].enabled ? 'À vous de répondre' : 'Micro coupé');
    }
    if (secondes >= DUREE_MAX) terminer();
}

$('micro').addEventListener('click', event => {
    const piste = direct.micro.getAudioTracks()[0];
    piste.enabled = !piste.enabled;
    event.target.textContent = piste.enabled ? 'Couper le micro' : 'Réactiver le micro';
});

// Liaison audio impossible avant le debut de l'entretien : on previent et on permet de reessayer
function echecAudio() {
    if (direct.debut) return terminer();  // coupure en cours d'entretien : on evalue ce qui a ete dit
    fermerConnexion();
    $('direct').hidden = true;
    $('demarrer').hidden = false;
    $('demarrer').disabled = false;
    statut.textContent = ERREUR_AUDIO;
}

function fermerConnexion() {
    clearInterval(direct.minuteur);
    clearTimeout(direct.attente);
    if (direct.canal) direct.canal.close();
    if (direct.connexion) direct.connexion.close();
    if (direct.micro) direct.micro.getTracks().forEach(piste => piste.stop());
    if (direct.son) direct.son.srcObject = null;
}

// ---------- 3. Fin de l'entretien et evaluation ----------
$('terminer').addEventListener('click', terminer);

async function terminer() {
    if (direct.fini) return;
    direct.fini = true;
    envoyer({type: 'session.close'});
    fermerConnexion();
    $('direct').querySelector('.boutons').hidden = true;
    $('etat').textContent = "Entretien terminé";
    statut.textContent = "La recruteuse rédige son évaluation...";
    try {
        const transcription = direct.messages.map(m => ({role: m.role, texte: m.texte.trim()})).filter(m => m.texte);
        const evaluation = await appeler('evaluation', {transcription: transcription});
        $('note').textContent = evaluation.note_globale;
        $('communication').textContent = evaluation.communication;
        $('competences').textContent = evaluation.competences_techniques;
        $('motivation').textContent = evaluation.motivation;
        $('verdict').textContent = evaluation.verdict;
        remplirListe('eval-forts', evaluation.points_forts);
        remplirListe('eval-axes', evaluation.axes_amelioration);
        remplirListe('conseils', evaluation.conseils.map(c => c.question + ' : ' + c.conseil));
        $('evaluation').hidden = false;
        statut.textContent = '';
    } catch (erreur) {
        statut.textContent = messageErreur(erreur);
    }
}
