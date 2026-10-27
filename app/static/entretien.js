// Simulation d'entretien : envoie la conversation a Flask et affiche la reponse de l'assistante DRH
const panneau = document.getElementById('entretien');
const statut = document.getElementById('statut');
const formulaire = document.getElementById('formulaire-reponse');
const zoneReponse = document.getElementById('reponse');
const historique = [];  // questions de l'assistante et reponses du candidat, dans l'ordre
const DELAI_MAX = 12000;  // millisecondes : au-dela, on previent l'utilisateur

// Ajoute une bulle de conversation (textContent : le texte n'est jamais interprete comme du HTML)
function ajouterMessage(texte, classe) {
    const bulle = document.createElement('p');
    bulle.className = 'bulle ' + classe;
    bulle.textContent = texte;
    document.getElementById('conversation').appendChild(bulle);
}

function remplirListe(id, elements) {
    const liste = document.getElementById(id);
    elements.forEach(texte => {
        const ligne = document.createElement('li');
        ligne.textContent = texte;
        liste.appendChild(ligne);
    });
}

async function envoyer() {
    statut.textContent = "L'assistante réfléchit...";
    formulaire.hidden = true;
    try {
        const reponse = await fetch(panneau.dataset.url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
            },
            body: JSON.stringify({historique: historique}),
            signal: AbortSignal.timeout(DELAI_MAX),
        });
        const donnees = await reponse.json();
        if (!reponse.ok) throw new Error(donnees.erreur);
        statut.textContent = '';
        return donnees;
    } catch (erreur) {
        statut.textContent = erreur.name === 'TimeoutError'
            ? "L'assistante met trop de temps à répondre. Réessayez."
            : (erreur.message || 'Erreur de connexion. Réessayez.');
        return null;
    }
}

// Affiche l'evaluation de fin d'entretien
function afficherEvaluation(evaluation) {
    document.getElementById('note').textContent = evaluation.note_globale;
    document.getElementById('communication').textContent = evaluation.communication;
    document.getElementById('competences').textContent = evaluation.competences_techniques;
    document.getElementById('motivation').textContent = evaluation.motivation;
    document.getElementById('verdict').textContent = evaluation.verdict;
    remplirListe('eval-forts', evaluation.points_forts);
    remplirListe('eval-axes', evaluation.axes_amelioration);
    remplirListe('conseils', evaluation.conseils.map(c => c.question + ' : ' + c.conseil));
    document.getElementById('evaluation').hidden = false;
}

// Affiche la question suivante
function poserQuestion(question) {
    historique.push(question);
    ajouterMessage(question, 'assistante');
    formulaire.hidden = false;
    zoneReponse.focus();
}

document.getElementById('demarrer').addEventListener('click', async event => {
    event.target.disabled = true;
    const analyse = await envoyer();
    if (!analyse) {
        event.target.disabled = false;
        return;
    }
    event.target.hidden = true;
    document.getElementById('score').textContent = analyse.compatibilite;
    document.getElementById('resume').textContent = analyse.resume;
    remplirListe('forts', analyse.points_forts);
    remplirListe('faibles', analyse.points_a_ameliorer);
    remplirListe('manquantes', analyse.competences_manquantes);
    remplirListe('recommandations', analyse.recommandations);
    document.getElementById('analyse').hidden = false;
    poserQuestion(analyse.question);
});

formulaire.addEventListener('submit', async event => {
    event.preventDefault();
    const texte = zoneReponse.value.trim();
    if (!texte) return;
    historique.push(texte);
    ajouterMessage(texte, 'candidat');
    zoneReponse.value = '';
    const suite = await envoyer();
    if (!suite) {
        historique.pop();  // la reponse n'a pas ete traitee : le candidat peut la renvoyer
        zoneReponse.value = texte;
        document.getElementById('conversation').lastChild.remove();
        formulaire.hidden = false;
        return;
    }
    if (suite.question) {
        poserQuestion(suite.question);
    } else {
        ajouterMessage(suite.conclusion, 'fin');  // fin de l'entretien : remerciement puis evaluation
        afficherEvaluation(suite.evaluation);
    }
});
