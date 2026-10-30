// Assistante DRH : analyse du CV, entretien vocal en direct (gpt-live-1 via WebRTC) puis evaluation.
// Le son passe directement entre le navigateur et OpenAI ; Flask cree seulement la session.
// Utilise envoyerAuServeur(), avecBulle() et attendre() de site.js.
const panneau = document.getElementById('assistante');
const statut = document.getElementById('statut');
const RAPPEL_FIN = 60;        // secondes avant la fin : la recruteuse recoit la consigne de conclure
const CONNEXION_MAX = 7000;   // millisecondes pour etablir la liaison audio (total sous 10 s)
const SEUIL_VOIX = 18;        // volume moyen (0 a 255) au-dessus duquel on considere que quelqu'un parle
const ERREUR_AUDIO = "La liaison audio n'a pas pu s'établir (réseau ou pare-feu). Réessayez sur une autre connexion.";
const COUPURE = "L'entretien s'est arrêté avant votre première réponse (liaison audio interrompue). Vous pouvez le relancer.";
const SANS_REPONSE = "Entretien arrêté avant votre première réponse : il n'y a rien à évaluer. Vous pouvez le relancer.";

const direct = {connexion: null, canal: null, micro: null, son: null, audio: null, analyseurs: {}, messages: [],
                debut: 0, minuteur: null, dernierSon: {}, accueil: '', fini: false, attente: null,
                conclusion: '', duree: 0, rappel: false};

const $ = id => document.getElementById(id);

// Adresse d'une etape : data-url se termine par /analyse, on remplace ce dernier mot
function appeler(etape, donnees = {}) {
    return envoyerAuServeur(panneau.dataset.url.replace(/[^/]+$/, etape), donnees);
}

function messageErreur(erreur) {
    if (erreur.name === 'TimeoutError') return "L'assistante met trop de temps à répondre. Réessayez.";
    if (erreur.name === 'NotAllowedError') return "Autorisez l'accès au micro pour passer l'entretien.";
    return erreur.message || 'Erreur de connexion. Réessayez.';
}

// Cree un element avec son texte. textContent : le texte de l'IA n'est jamais interprete comme du HTML.
function element(balise, texte, classe = '') {
    const noeud = document.createElement(balise);
    noeud.textContent = texte;
    if (classe) noeud.className = classe;
    return noeud;
}

function anneau(note) {
    const bloc = document.createElement('div');
    bloc.className = 'anneau';
    bloc.style.setProperty('--n', note);
    bloc.innerHTML = '<svg viewBox="0 0 100 100"><circle class="piste" cx="50" cy="50" r="45"/>'
                   + '<circle class="valeur" cx="50" cy="50" r="45"/></svg>';
    bloc.appendChild(element('b', note));
    return bloc;
}

// Note + phrase a cote de l'anneau
function score(note, titre, texte) {
    const bloc = element('div', '', 'score');
    const phrase = element('p', '');
    phrase.append(element('b', titre), document.createElement('br'), texte);
    bloc.append(anneau(note), phrase);
    return bloc;
}

// Ajoute dans "bloc" un titre et des pastilles (competences)
function ajouterPuces(bloc, titre, noms, classe) {
    const ligne = element('div', '', 'puces');
    noms.forEach(nom => ligne.appendChild(element('span', nom, 'puce ' + classe)));
    bloc.append(element('p', titre, 'etiquette-puces'), ligne);
}

// Ajoute dans "bloc" un titre et une liste numerotee (conseils)
function ajouterListe(bloc, titre, textes) {
    const liste = element('ol', '', 'liste-conseils');
    textes.forEach(texte => liste.appendChild(element('li', texte)));
    bloc.append(element('p', titre, 'etiquette-puces'), liste);
}

// ---------- 1. Analyse ecrite du CV ----------
$('analyser').addEventListener('click', async () => {
    const bouton = $('analyser');
    const texteBouton = bouton.innerHTML;
    statut.textContent = '';
    try {
        const analyse = await avecBulle(bouton, $('bulle-analyse'), 'Analyse en cours', () => appeler('analyse'));
        bouton.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-coche"/></svg> Analyse terminée';
        const bloc = $('analyse');
        bloc.append(score(analyse.compatibilite, analyse.compatibilite + ' % de compatibilité.', analyse.resume));
        ajouterPuces(bloc, 'Vos points forts', analyse.points_forts, '');
        ajouterPuces(bloc, 'Compétences à ajouter', analyse.competences_manquantes, 'renforcer');
        ajouterListe(bloc, 'Points à améliorer', analyse.points_a_ameliorer);
        ajouterListe(bloc, 'Conseils pour votre CV', analyse.recommandations);
        bloc.hidden = false;
    } catch (erreur) {
        bouton.innerHTML = texteBouton;
        statut.textContent = messageErreur(erreur);
    }
});

// ---------- 2. Entretien vocal en direct ----------
async function demarrer() {
    if (direct.connexion || direct.fini) return;
    panneau.scrollIntoView({behavior: 'smooth', block: 'start'});
    $('demarrer').disabled = true;
    statut.textContent = '';
    try {
        // Mesure le volume des deux voix pour dessiner l'onde. Cree tout de suite, pendant le clic : sur iPhone,
        // un AudioContext cree apres une attente (ici, l'autorisation du micro) reste en pause
        direct.audio = new AudioContext();
        direct.micro = await navigator.mediaDevices.getUserMedia({audio: true});
        direct.analyseurs.candidat = analyseur(direct.micro);
        direct.connexion = new RTCPeerConnection();
        direct.son = new Audio();
        direct.son.autoplay = true;
        direct.connexion.ontrack = e => {
            direct.son.srcObject = e.streams[0];
            direct.analyseurs.recruteur = analyseur(e.streams[0]);
        };
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
        direct.conclusion = session.conclusion;
        direct.duree = session.duree;  // secondes, fixee par le serveur (DUREE_ENTRETIEN dans ia.py)
        await direct.connexion.setRemoteDescription({type: 'answer', sdp: session.sdp});
        // Sans session.started dans le delai, la liaison audio est consideree comme bloquee
        direct.attente = setTimeout(echecAudio, CONNEXION_MAX);
        $('accueil-assistante').hidden = true;
        $('direct').hidden = false;
        // Pendant l'entretien, la barre du bas du telephone disparait (voir style.css)
        document.body.classList.add('entretien-en-cours');
        $('etat-recruteuse').textContent = 'En entretien avec vous';
        requestAnimationFrame(dessinerOnde);
    } catch (erreur) {
        signaler('démarrage impossible : ' + erreur.name + ' ' + erreur.message);
        recommencer(messageErreur(erreur));
    }
}
$('demarrer').addEventListener('click', demarrer);
$('lancer').addEventListener('click', demarrer);  // grand bouton mauve de l'en-tete

// Un analyseur Web Audio donne, plusieurs fois par seconde, le volume de chaque frequence d'un son
function analyseur(flux) {
    const noeud = direct.audio.createAnalyser();
    noeud.fftSize = 64;
    direct.audio.createMediaStreamSource(flux).connect(noeud);
    return noeud;
}

function volume(noeud) {
    const valeurs = new Uint8Array(noeud.frequencyBinCount);
    noeud.getByteFrequencyData(valeurs);
    let total = 0;
    for (const valeur of valeurs) total += valeur;
    return {valeurs: valeurs, moyenne: total / valeurs.length};
}

// L'onde suit la voix : bleue quand la recruteuse parle, mauve quand le candidat parle
function dessinerOnde() {
    if (direct.fini || !direct.connexion) return;  // entretien fini ou a relancer : l'animation s'arrete
    let parle = null;
    let son = null;
    for (const qui of ['recruteur', 'candidat']) {
        if (!direct.analyseurs[qui]) continue;
        const mesure = volume(direct.analyseurs[qui]);
        if (mesure.moyenne > SEUIL_VOIX && (!son || mesure.moyenne > son.moyenne)) {
            parle = qui;
            son = mesure;
        }
    }
    if (parle) direct.dernierSon[parle] = Date.now();
    $('onde').className = 'onde-vocale ' + (parle || '');
    const barres = $('onde').querySelectorAll('i');
    const milieu = (barres.length - 1) / 2;
    barres.forEach((barre, i) => {
        // Les sons graves (les plus forts) au centre, les aigus vers les bords : l'onde est symetrique
        const frequence = Math.floor(Math.abs(i - milieu));
        const valeur = son ? son.valeurs[frequence] : 0;
        barre.style.height = (8 + valeur / 255 * 92) + '%';
    });
    requestAnimationFrame(dessinerOnde);
}

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
        $('qui-parle').textContent = 'La recruteuse arrive...';
    } else if (evenement.type === 'session.output_transcript.delta') {
        ajouterTexte('recruteur', evenement.delta);
    } else if (evenement.type === 'session.input_transcript.delta') {
        ajouterTexte('candidat', evenement.delta);
    } else if (evenement.type === 'session.closed') {
        terminer('session fermée par OpenAI (' + evenement.reason + ')');  // coupure, expiration, filtre...
    } else if (evenement.type === 'error') {
        signaler('erreur OpenAI : ' + JSON.stringify(evenement).slice(0, 150));
    }
}

// Les fragments de texte arrivent mot par mot : on les regroupe par personne qui parle
function ajouterTexte(role, fragment) {
    let dernier = direct.messages[direct.messages.length - 1];
    if (!dernier || dernier.role !== role) {
        const bulle = element('p', '', 'bulle-texte ' + role);
        $('conversation').appendChild(bulle);
        dernier = {role: role, texte: '', bulle: bulle};
        direct.messages.push(dernier);
    }
    dernier.texte += fragment;
    dernier.bulle.textContent = dernier.texte;
    $('conversation').scrollTop = $('conversation').scrollHeight;
}

function chaqueSeconde() {
    const secondes = Math.floor((Date.now() - direct.debut) / 1000);
    $('temps').textContent = String(Math.floor(secondes / 60)).padStart(2, '0') + ':' + String(secondes % 60).padStart(2, '0');
    $('duree').style.width = (secondes / direct.duree * 100) + '%';
    const recent = qui => Date.now() - (direct.dernierSon[qui] || 0) < 1200;
    if (!direct.micro.getAudioTracks()[0].enabled) {
        $('qui-parle').textContent = 'Micro coupé';
    } else if (recent('recruteur')) {
        $('qui-parle').textContent = 'La recruteuse parle';
    } else if (recent('candidat')) {
        $('qui-parle').textContent = 'Vous parlez';
    } else if (direct.dernierSon.recruteur) {
        $('qui-parle').textContent = 'À vous de répondre';
    }
    // Une minute avant la fin, la recruteuse est priee de conclure : l'entretien ne s'arrete pas en pleine phrase.
    // Instruction silencieuse (instructions.append) : elle ne l'annonce pas et ne coupe pas la parole au candidat
    if (secondes >= direct.duree - RAPPEL_FIN && !direct.rappel) {
        direct.rappel = true;
        envoyer({type: 'session.instructions.append', delegation_id: null, content: direct.conclusion});
    }
    if (secondes >= direct.duree) terminer();  // l'entretien s'arrete tout seul (il est paye a la minute)
}

$('micro').addEventListener('click', () => {
    const piste = direct.micro.getAudioTracks()[0];
    piste.enabled = !piste.enabled;
    $('micro').classList.toggle('coupe', !piste.enabled);
    $('micro').querySelector('use').setAttribute('href', piste.enabled ? '#i-micro' : '#i-micro-coupe');
});

// Liaison audio impossible, ou coupee pendant l'entretien
function echecAudio() {
    if (direct.debut) return terminer('liaison audio coupée');  // on evalue ce qui a deja ete dit
    signaler('liaison audio impossible (état : ' + direct.connexion.connectionState + ')');
    recommencer(ERREUR_AUDIO);
}

// L'entretien n'a pas pu avoir lieu : on previent et on permet de le relancer sans recharger la page
function recommencer(message) {
    fermerConnexion();
    direct.connexion = null;
    direct.debut = 0;
    direct.fini = false;
    direct.rappel = false;
    direct.messages = [];
    direct.dernierSon = {};
    $('conversation').textContent = '';
    $('temps').textContent = '00:00';
    $('duree').style.width = '0';
    $('direct').hidden = true;
    $('accueil-assistante').hidden = false;
    $('demarrer').disabled = false;
    $('etat-recruteuse').textContent = 'Disponible';
    statut.textContent = message;
}

// Note un incident dans le journal du site (ENTRETIEN_INCIDENT) : c'est le seul moyen de comprendre une panne
// survenue sur le telephone d'un utilisateur. On n'attend pas la reponse et un echec d'envoi est ignore.
function signaler(raison) {
    appeler('incident', {raison: raison}).catch(() => {});
}
window.addEventListener('error', e => {
    if (direct.connexion) signaler('erreur JavaScript : ' + e.message);
});

function fermerConnexion() {
    document.body.classList.remove('entretien-en-cours');
    clearInterval(direct.minuteur);
    clearTimeout(direct.attente);
    if (direct.canal) direct.canal.close();
    if (direct.connexion) direct.connexion.close();
    if (direct.micro) direct.micro.getTracks().forEach(piste => piste.stop());
    if (direct.son) direct.son.srcObject = null;
    if (direct.audio) direct.audio.close();
    direct.audio = null;  // fermerConnexion peut etre appelee deux fois : un AudioContext ne se ferme qu'une fois
    direct.analyseurs = {};
}

// ---------- 3. Fin de l'entretien et evaluation ----------
$('terminer').addEventListener('click', () => terminer());

// raison : seulement si l'entretien s'arrete tout seul (coupure) ; elle est alors notee dans le journal
async function terminer(raison) {
    if (direct.fini) return;
    direct.fini = true;
    if (raison) signaler(raison + ' après ' + Math.floor((Date.now() - direct.debut) / 1000) + ' s');
    envoyer({type: 'session.close'});
    fermerConnexion();
    const transcription = direct.messages.map(m => ({role: m.role, texte: m.texte.trim()})).filter(m => m.texte);
    // Arret avant la premiere reponse du candidat : rien a evaluer, on propose de relancer l'entretien
    if (!transcription.some(m => m.role === 'candidat')) return recommencer(raison ? COUPURE : SANS_REPONSE);
    $('direct').hidden = true;
    $('evaluation').hidden = false;
    $('etat-recruteuse').textContent = 'Entretien terminé';
    $('attente-evaluation').querySelector('.bulle').classList.add('en-cours');
    try {
        const evaluation = await appeler('evaluation', {transcription: transcription});
        afficherEvaluation(evaluation);
    } catch (erreur) {
        $('attente-evaluation').hidden = true;
        statut.textContent = messageErreur(erreur);
    }
}

function afficherEvaluation(evaluation) {
    $('attente-evaluation').hidden = true;
    const bloc = $('resultat-evaluation');
    bloc.append(score(evaluation.note_globale, evaluation.note_globale + ' / 100.', evaluation.verdict));

    // Trois barres qui se remplissent : chaque note est sur 10
    const NOTES = [{nom: 'Communication', note: evaluation.communication},
                   {nom: 'Compétences techniques', note: evaluation.competences_techniques},
                   {nom: 'Motivation', note: evaluation.motivation}];
    const barres = element('div', '', 'barres');
    NOTES.forEach(ligne => {
        const jauge = element('span', '', 'jauge');
        const remplissage = document.createElement('i');
        remplissage.style.setProperty('--n', (ligne.note * 10) + '%');
        jauge.appendChild(remplissage);
        const rangee = document.createElement('div');
        rangee.append(element('span', ligne.nom), element('b', ligne.note + ' / 10'), jauge);
        barres.appendChild(rangee);
    });
    bloc.append(barres);
    ajouterPuces(bloc, 'Vos points forts', evaluation.points_forts, '');
    ajouterListe(bloc, "Axes d'amélioration", evaluation.axes_amelioration);

    if (evaluation.conseils.length) {
        bloc.append(element('p', 'Réponses à retravailler', 'etiquette-puces'));
        evaluation.conseils.forEach(conseil => {
            const details = document.createElement('details');
            details.append(element('summary', conseil.question), element('p', conseil.conseil));
            bloc.append(details);
        });
    }
    const refaire = element('a', '', 'btn mauve');
    refaire.href = location.pathname + '#assistante';
    refaire.innerHTML = '<svg class="icone" aria-hidden="true"><use href="#i-micro"/></svg> Refaire un entretien';
    refaire.addEventListener('click', () => location.reload());
    const historique = element('a', 'Voir mon historique', 'btn clair');
    historique.href = panneau.dataset.historique;
    bloc.append(refaire, historique);
    bloc.hidden = false;
}
