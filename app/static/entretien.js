// Assistante DRH : analyse du CV, entretien vocal en direct (gpt-live-1 via WebRTC) puis evaluation.
// Le son passe directement entre le navigateur et OpenAI ; Flask cree seulement la session.
// Utilise envoyerAuServeur() de site.js.
const panneau = document.getElementById('assistante');
const statut = document.getElementById('statut');
const DUREE_MIN = 3000;       // millisecondes : la bulle d'analyse a toujours le temps de se remplir
const DUREE_MAX = 10 * 60;    // secondes : l'entretien s'arrete tout seul (il est paye a la minute)
const CONNEXION_MAX = 7000;   // millisecondes pour etablir la liaison audio (total sous 10 s)
const SEUIL_VOIX = 18;        // volume moyen (0 a 255) au-dessus duquel on considere que quelqu'un parle
const ERREUR_AUDIO = "La liaison audio n'a pas pu s'établir (réseau ou pare-feu). Réessayez sur une autre connexion.";

const direct = {connexion: null, canal: null, micro: null, son: null, audio: null, analyseurs: {}, messages: [],
                debut: 0, minuteur: null, dernierSon: {}, accueil: '', fini: false, attente: null};

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

function attendre(millisecondes) {
    return new Promise(fin => setTimeout(fin, millisecondes));
}

// Bouton mauve + bulle qui se remplit, puis bleu "terminee" (comme sur la page d'envoi du CV)
async function avecBulle(bouton, bulle, texteEnCours, travail) {
    bouton.disabled = true;
    bouton.classList.add('en-cours');
    bouton.textContent = texteEnCours;
    bulle.hidden = false;
    setTimeout(() => bulle.classList.add('en-cours'), 50);
    const debut = Date.now();
    try {
        const resultat = await travail();
        await attendre(Math.max(0, DUREE_MIN - (Date.now() - debut)));
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
        direct.micro = await navigator.mediaDevices.getUserMedia({audio: true});
        direct.audio = new AudioContext();  // mesure le volume des deux voix pour dessiner l'onde
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
        await direct.connexion.setRemoteDescription({type: 'answer', sdp: session.sdp});
        // Sans session.started dans le delai, la liaison audio est consideree comme bloquee
        direct.attente = setTimeout(echecAudio, CONNEXION_MAX);
        $('accueil-assistante').hidden = true;
        $('direct').hidden = false;
        $('etat-recruteuse').textContent = 'En entretien avec vous';
        requestAnimationFrame(dessinerOnde);
    } catch (erreur) {
        fermerConnexion();
        direct.connexion = null;
        statut.textContent = messageErreur(erreur);
        $('demarrer').disabled = false;
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
    if (direct.fini) return;
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
    $('onde').querySelectorAll('i').forEach((barre, i) => {
        const valeur = son ? son.valeurs[i % son.valeurs.length] : 0;
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
        terminer();  // session coupee ou expiree
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
    $('duree').style.width = (secondes / DUREE_MAX * 100) + '%';
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
    if (secondes >= DUREE_MAX) terminer();
}

$('micro').addEventListener('click', () => {
    const piste = direct.micro.getAudioTracks()[0];
    piste.enabled = !piste.enabled;
    $('micro').classList.toggle('coupe', !piste.enabled);
    $('micro').querySelector('use').setAttribute('href', piste.enabled ? '#i-micro' : '#i-micro-coupe');
});

// Liaison audio impossible avant le debut de l'entretien : on previent et on permet de reessayer
function echecAudio() {
    if (direct.debut) return terminer();  // coupure en cours d'entretien : on evalue ce qui a ete dit
    fermerConnexion();
    direct.connexion = null;
    $('direct').hidden = true;
    $('accueil-assistante').hidden = false;
    $('demarrer').disabled = false;
    $('etat-recruteuse').textContent = 'Disponible';
    statut.textContent = ERREUR_AUDIO;
}

function fermerConnexion() {
    clearInterval(direct.minuteur);
    clearTimeout(direct.attente);
    if (direct.canal) direct.canal.close();
    if (direct.connexion) direct.connexion.close();
    if (direct.micro) direct.micro.getTracks().forEach(piste => piste.stop());
    if (direct.son) direct.son.srcObject = null;
    if (direct.audio) direct.audio.close();
    direct.analyseurs = {};
}

// ---------- 3. Fin de l'entretien et evaluation ----------
$('terminer').addEventListener('click', terminer);

async function terminer() {
    if (direct.fini) return;
    direct.fini = true;
    envoyer({type: 'session.close'});
    fermerConnexion();
    $('direct').hidden = true;
    $('evaluation').hidden = false;
    $('etat-recruteuse').textContent = 'Entretien terminé';
    $('attente-evaluation').querySelector('.bulle').classList.add('en-cours');
    try {
        const transcription = direct.messages.map(m => ({role: m.role, texte: m.texte.trim()})).filter(m => m.texte);
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
