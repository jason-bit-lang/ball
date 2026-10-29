import re
import uuid
from datetime import timedelta
import requests
from sqlalchemy import text
from flask import Response, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from config import ADRESSE_API
from pipeline.nettoyage_offres import trouver_competences
from . import app, db
from .affichage import decouper_description, echeance, maniere_de_postuler
from .ia import (TEXTE_MIN, IAIndisponible, analyser_candidature, creer_entretien_vocal, evaluer_entretien,
                 extraire_texte)
from .journal import log_event
from .matching import comparer, cv_reconnu, offres_recentes, rechercher
from .models import Document, EntretienVocal, Favori, Offre, User, now_utc

# Extensions acceptees et premiers octets attendus pour chacune
# (un PDF commence par %PDF, un DOCX est une archive zip qui commence par PK)
SIGNATURES = {'pdf': b'%PDF', 'docx': b'PK\x03\x04'}
EMAIL_REGEX = r'[^@\s]+@[^@\s]+\.[^@\s]+'
PASSWORD_MIN_LENGTH = 8
NOM_MAX, EMAIL_MAX = 100, 150  # tailles des colonnes de la table User
STATUT_ANALYSE = 'CV analysé'
# Assistante DRH : passer a False pour la masquer (par exemple si le credit OpenAI est epuise)
ASSISTANTE_ACTIVE = True
ENTRETIENS_PAR_JOUR = 5   # chaque entretien vocal est payant : limite par utilisateur sur 24 h
PITCH_DELAI = 10          # secondes laissees a l'API du pitch (elle repond en moins de 9,5 s)
SDP_MAX = 20000           # taille maximale de l'offre WebRTC envoyee par le navigateur
ROLES = {'recruteur', 'candidat'}
CV_ILLISIBLE = ("Nous n'avons pas pu analyser correctement votre CV. Veuillez envoyer un autre CV, "
                "ou une autre version de votre CV, pour que nous puissions l'analyser correctement.")


def form_value(name):
    """Lit un champ du formulaire sans planter s'il est absent, sans espaces autour."""
    return request.form.get(name, '').strip()


def safe_next_page():
    """Page demandee avant la connexion, seulement si elle est sur ce site."""
    next_page = request.args.get('next', '')
    if next_page.startswith('/') and not next_page.startswith('//'):
        return next_page
    return url_for('index')


def file_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def cv_error(file):
    """Verifie l'extension ET le vrai contenu du fichier. Renvoie la raison du refus, ou None si tout va bien."""
    signature = SIGNATURES.get(file_extension(file.filename))
    if signature is None:
        return 'bad_extension'
    debut = file.stream.read(len(signature))
    file.stream.seek(0)  # remet la lecture au debut pour pouvoir enregistrer le fichier
    return None if debut == signature else 'bad_signature'


def document_du_user(id):
    """Un utilisateur ne peut ouvrir que ses propres documents (sinon erreur 404)."""
    return Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()


def demande_du_script():
    """Vrai si la demande vient du script de la page d'envoi (envoi.js) : on lui repond en JSON."""
    return request.headers.get('X-Requested-With') == 'fetch'


def refuser_envoi(message):
    """Envoi refuse : message en JSON pour le script de la page, sinon message flash et retour a la page."""
    if demande_du_script():
        return jsonify(erreur=message), 400
    flash(message, 'erreur')
    return redirect(url_for('upload'))


def reject_upload(reason, message, filename=''):
    """Refus d'un envoi : on le note dans le journal puis on previent l'utilisateur."""
    log_event('UPLOAD_REJECTED', reason=reason, file=filename,
              ext=file_extension(filename), size=request.content_length or 0)
    return refuser_envoi(message)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nom = form_value('nom')
        prenom = form_value('prenom')
        email = form_value('email').lower()
        password = request.form.get('password', '')
        confirmation = request.form.get('confirmation_mot_secret', '')

        # Une seule erreur est affichee a la fois, la premiere trouvee
        if not (nom and prenom and email and password):
            error = 'Veuillez remplir tous les champs.'
        elif len(nom) > NOM_MAX or len(prenom) > NOM_MAX or len(email) > EMAIL_MAX:
            error = f'Nom et prénom : {NOM_MAX} caractères maximum ; email : {EMAIL_MAX} caractères maximum.'
        elif not re.fullmatch(EMAIL_REGEX, email):
            error = 'Adresse email invalide.'
        elif len(password) < PASSWORD_MIN_LENGTH:
            error = f'Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères.'
        elif password != confirmation:
            error = 'Les mots de passe ne correspondent pas.'
        elif User.query.filter_by(email=email).first():
            error = 'Cet email est déjà utilisé.'
        else:
            error = None

        if error:
            # L'erreur s'affiche dans la carte du formulaire ; les champs gardent leur valeur
            return render_template('register.html', form=request.form, erreur=error)

        user = User(nom=nom, prenom=prenom, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # Connexion automatique : le nouvel utilisateur arrive directement sur l'envoi de son CV
        login_user(user)
        flash(f'Bienvenue sur CVBoost, {user.prenom}.', 'succes')
        return redirect(url_for('upload'))

    return render_template('register.html', form={}, erreur=None)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = form_value('email').lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        # Meme message si l'email ou le mot de passe est faux :
        # on ne revele pas quels emails existent
        if user is None or not user.check_password(password):
            log_event('LOGIN_FAIL', email=email)
            return render_template('login.html', email=email, erreur='Email ou mot de passe incorrect.')

        login_user(user)
        log_event('LOGIN_OK', email=email)
        flash(f'Bon retour, {user.prenom}.', 'succes')
        return redirect(safe_next_page())

    return render_template('login.html', email='', erreur=None)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('cv')
        if not file or file.filename == '':
            return reject_upload('empty', 'Aucun fichier sélectionné.')
        original_filename = secure_filename(file.filename)
        error = cv_error(file)
        if error:
            return reject_upload(error, 'Fichier invalide : seuls les vrais fichiers PDF ou DOCX sont acceptés.',
                                 original_filename)

        # Le CV est lu tout de suite. Il est refuse seulement si rien n'y est reconnu
        # (scan sans texte, ou texte sans aucune competence ni aucun mot en commun avec les offres).
        extension = file_extension(original_filename)
        contenu = file.read()
        texte = extraire_texte(contenu, extension)
        log_event('UPLOAD_OK', file=original_filename, ext=extension, size=len(contenu))
        if len(texte) < TEXTE_MIN or not cv_reconnu(texte):
            log_event('CV_ILLISIBLE', file=original_filename)
            return refuser_envoi(CV_ILLISIBLE)

        # Le fichier et son texte sont enregistres dans la base. Le nom unique (UUID) evite toute
        # confusion entre deux CV qui portent le meme nom.
        document = Document(original_filename=original_filename, stored_filename=f'{uuid.uuid4()}.{extension}',
                            contenu=contenu, texte=texte, status=STATUT_ANALYSE, user_id=current_user.id)
        db.session.add(document)
        db.session.commit()
        adresse = url_for('recherche', id=document.id)
        if demande_du_script():
            return jsonify(adresse=adresse)
        return redirect(adresse)

    return render_template('upload.html')


@app.route('/health')
def health():
    """Route de sante : Render et UptimeRobot l'appellent pour savoir si le site va bien (et le garder eveille)."""
    try:
        db.session.execute(text('SELECT 1'))
        base = 'ok'
    except Exception:
        db.session.rollback()
        base = 'erreur'
    try:
        api = 'ok' if requests.get(ADRESSE_API + '/health', timeout=2).ok else 'erreur'
    except requests.RequestException:
        api = 'erreur'
    # Sans base de donnees, le site ne peut pas fonctionner : code 503 pour que Render le signale
    return jsonify(site='ok', base=base, api=api), 200 if base == 'ok' else 503


@app.errorhandler(404)
def page_introuvable(erreur):
    return render_template('erreur.html', titre='Page introuvable.',
                           message="Cette page n'existe pas ou a été déplacée."), 404


@app.errorhandler(500)
def erreur_serveur(erreur):
    # Flask a deja ecrit le detail de l'erreur dans le journal (console de Render)
    return render_template('erreur.html', titre='Un problème est survenu.',
                           message="L'erreur a été enregistrée. Réessayez dans un instant."), 500


@app.errorhandler(413)
def file_too_large(error):
    # Le fichier est refuse avant d'etre lu : son nom est inconnu, seule la taille est notee
    return reject_upload('too_large', 'Fichier trop volumineux : 5 Mo maximum.')


def derniere_note(offre_id):
    """Note du dernier entretien vocal evalue sur cette offre, ou None."""
    entretien = (EntretienVocal.query.filter_by(user_id=current_user.id, offre_id=offre_id)
                 .filter(EntretienVocal.note.isnot(None)).order_by(EntretienVocal.date.desc()).first())
    return entretien.note if entretien else None


@app.route('/history')
@login_required
def history():
    """Historique : offres favorites (avec leur date de cloture et la derniere note) et CV lisibles."""
    documents = (Document.query.filter_by(user_id=current_user.id, status=STATUT_ANALYSE)
                 .order_by(Document.upload_date.desc()).all())
    cvs = [{'document': document, 'competences': trouver_competences(document.texte)} for document in documents]
    favoris = Favori.query.filter_by(user_id=current_user.id).order_by(Favori.date.desc()).all()
    cartes = [{'offre': favori.offre, 'echeance': echeance(favori.offre), 'note': derniere_note(favori.offre_id)}
              for favori in favoris]
    dernier_cv = documents[0] if documents else None
    return render_template('history.html', favoris=cartes, cvs=cvs, dernier_cv=dernier_cv)


@app.route('/recherche/<int:id>')
@login_required
def recherche(id):
    """Page des opportunites : offres ouvertes les plus proches du CV (matching TF-IDF).
    Elle n'est jamais vide : sans offre en commun avec le CV, on propose les plus recentes."""
    document = document_du_user(id)
    texte = document.texte
    if not texte:
        flash(CV_ILLISIBLE, 'erreur')
        return redirect(url_for('upload'))
    resultats = rechercher(texte) or offres_recentes(texte)
    proches = [resultat for resultat in resultats if resultat['niveau'] != 'explorer']
    log_event('RECHERCHE', cv=document.id, resultats=len(resultats))
    return render_template('resultats.html', document=document, resultats=resultats, proches=len(proches),
                           competences=trouver_competences(texte))


@app.route('/offre/<int:offre_id>/cv/<int:id>')
@login_required
def offre(offre_id, id):
    """Detail d'une offre, avec l'assistante DRH a cote."""
    offre = db.get_or_404(Offre, offre_id)
    document = document_du_user(id)
    texte = document.texte
    # Niveau de l'offre si elle fait partie des resultats du CV, sinon "a explorer"
    resultat = next((r for r in rechercher(texte) if r['offre'].id == offre.id), None) if texte else None
    if resultat is None:
        resultat = comparer(offre, set(trouver_competences(texte)))
    sections = decouper_description(offre.description)
    dossier = next((section for section in sections if 'candidature' in section['titre'].lower()), None)
    favori = Favori.query.filter_by(user_id=current_user.id, offre_id=offre.id).first() is not None
    return render_template('offre.html', offre=offre, document=document, resultat=resultat, sections=sections,
                           dossier=dossier, favori=favori, echeance=echeance(offre),
                           postuler=maniere_de_postuler(offre), assistante=ASSISTANTE_ACTIVE)


@app.route('/pitch/<int:id>', methods=['POST'])
@login_required
def pitch(id):
    """Pitch vocal du CV : le site demande le son a l'API FastAPI (api/main.py) puis le renvoie au navigateur."""
    document = document_du_user(id)  # un utilisateur n'ecoute que le pitch de ses propres CV
    try:
        reponse = requests.post(ADRESSE_API + '/speak-smart', json={'document_id': document.id}, timeout=PITCH_DELAI)
        reponse.raise_for_status()
    except requests.RequestException as erreur:
        log_event('PITCH_ERREUR', cv=document.id, erreur=type(erreur).__name__)
        return jsonify(erreur="Votre pitch n'est pas disponible pour le moment. Réessayez dans un instant."), 503
    log_event('PITCH', cv=document.id)
    return Response(reponse.content, mimetype='audio/mpeg',
                    headers={'X-Pitch-Texte': reponse.headers.get('X-Pitch-Texte', '')})


@app.route('/favori/<int:offre_id>', methods=['POST'])
@login_required
def favori(offre_id):
    """Bouton coeur : ajoute l'offre aux favoris, ou l'en retire si elle y est deja."""
    offre = db.get_or_404(Offre, offre_id)
    existant = Favori.query.filter_by(user_id=current_user.id, offre_id=offre.id).first()
    if existant:
        db.session.delete(existant)
    else:
        db.session.add(Favori(user_id=current_user.id, offre_id=offre.id))
    db.session.commit()
    return jsonify(favori=existant is None)


def entretiens_du_jour():
    hier = now_utc() - timedelta(days=1)
    return EntretienVocal.query.filter(EntretienVocal.user_id == current_user.id, EntretienVocal.date > hier).count()


def transcription_valide(transcription):
    """Liste de messages {'role': 'recruteur' ou 'candidat', 'texte': '...'} avec au moins une reponse."""
    return (isinstance(transcription, list)
            and all(isinstance(m, dict) and m.get('role') in ROLES and isinstance(m.get('texte'), str)
                    for m in transcription)
            and any(m['role'] == 'candidat' and m['texte'].strip() for m in transcription))


@app.route('/entretien/<int:offre_id>/cv/<int:id>/<etape>', methods=['POST'])
@login_required
def entretien(offre_id, id, etape):
    """Assistante DRH en trois etapes, appelees par static/entretien.js :
    analyse -> analyse ecrite du CV pour cette offre
    vocal -> cree la session vocale (le navigateur envoie son offre WebRTC "sdp")
    evaluation -> note l'entretien a partir de sa transcription"""
    if not ASSISTANTE_ACTIVE or etape not in ('analyse', 'vocal', 'evaluation'):
        return jsonify(erreur="L'assistante DRH n'est pas disponible."), 404
    offre = db.get_or_404(Offre, offre_id)
    texte = document_du_user(id).texte
    if not texte:
        return jsonify(erreur='Le texte de ce CV est illisible : envoyez une autre version.'), 400
    donnees = request.get_json(silent=True) or {}

    try:
        if etape == 'analyse':
            reponse = analyser_candidature(texte, offre)
        elif etape == 'vocal':
            sdp = donnees.get('sdp')
            if not isinstance(sdp, str) or not sdp.startswith('v=0') or len(sdp) > SDP_MAX:
                return jsonify(erreur='Connexion audio invalide.'), 400
            if entretiens_du_jour() >= ENTRETIENS_PAR_JOUR:
                return jsonify(erreur=f'Limite atteinte : {ENTRETIENS_PAR_JOUR} entretiens vocaux par jour.'), 429
            reponse = creer_entretien_vocal(texte, offre, sdp)
            db.session.add(EntretienVocal(user_id=current_user.id, offre_id=offre.id))
            db.session.commit()
        else:
            transcription = donnees.get('transcription')
            if not transcription_valide(transcription):
                return jsonify(erreur="Aucune réponse enregistrée : l'entretien ne peut pas être évalué."), 400
            reponse = evaluer_entretien(texte, offre, transcription)
            # La note est gardee pour l'historique, sur le dernier entretien lance pour cette offre
            dernier = (EntretienVocal.query.filter_by(user_id=current_user.id, offre_id=offre.id)
                       .order_by(EntretienVocal.date.desc()).first())
            if dernier:
                dernier.note = reponse['note_globale']
                db.session.commit()
    except IAIndisponible as erreur:
        log_event('IA_ERREUR', cv=id, offre=offre_id, etape=etape, cause=repr(erreur.__cause__))
        return jsonify(erreur=str(erreur)), 503
    log_event('ENTRETIEN', cv=id, offre=offre_id, etape=etape)
    return jsonify(reponse)
