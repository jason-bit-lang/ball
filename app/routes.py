import os
import re
import uuid
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from . import app, db
from .ia import TEXTE_MIN, IAIndisponible, analyser_candidature, extraire_texte, question_suivante
from .journal import log_event
from .matching import rechercher
from .models import Document, Offre, User

# Extensions acceptees et premiers octets attendus pour chacune
# (un PDF commence par %PDF, un DOCX est une archive zip qui commence par PK)
SIGNATURES = {'pdf': b'%PDF', 'docx': b'PK\x03\x04'}
EMAIL_REGEX = r'[^@\s]+@[^@\s]+\.[^@\s]+'
PASSWORD_MIN_LENGTH = 8
STATUT_ANALYSE = 'CV analysé'
STATUT_ILLISIBLE = 'CV illisible (scanné ou abîmé)'
# Assistante DRH codee mais masquee pour le moment : passer a True pour l'afficher
ASSISTANTE_ACTIVE = False


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


def texte_du_cv(document):
    """Lit le texte du CV et met a jour son statut. Les deux IA (matching et assistante DRH) l'utilisent.
    Renvoie une chaine vide si le CV est illisible."""
    texte = extraire_texte(os.path.join(app.config['UPLOAD_FOLDER'], document.stored_filename))
    statut = STATUT_ANALYSE if len(texte) >= TEXTE_MIN else STATUT_ILLISIBLE
    if document.status != statut:
        document.status = statut
        db.session.commit()
    return texte if statut == STATUT_ANALYSE else ''


def reject_upload(reason, message, filename=''):
    """Refus d'un envoi : on le note dans le journal puis on previent l'utilisateur."""
    log_event('UPLOAD_REJECTED', reason=reason, file=filename,
              ext=file_extension(filename), size=request.content_length or 0)
    flash(message, 'danger')
    return redirect(url_for('upload'))


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
            flash(error, 'danger')
            return render_template('register.html', form=request.form)

        user = User(nom=nom, prenom=prenom, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Inscription réussie. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form={})


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
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('login.html', email=email)

        login_user(user)
        log_event('LOGIN_OK', email=email)
        flash(f'Bienvenue {user.prenom}.', 'success')
        return redirect(safe_next_page())

    return render_template('login.html', email='')


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

        # Le fichier est renomme avec un identifiant unique (UUID) :
        # deux CV portant le meme nom ne s'ecrasent jamais
        stored_filename = f'{uuid.uuid4()}.{file_extension(original_filename)}'
        path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(path)
        log_event('UPLOAD_OK', file=original_filename, ext=file_extension(original_filename),
                  size=os.path.getsize(path), stored=stored_filename)

        document = Document(original_filename=original_filename,
                            stored_filename=stored_filename,
                            user_id=current_user.id)
        db.session.add(document)
        db.session.commit()
        # Le CV est lu tout de suite : l'utilisateur sait immediatement s'il est exploitable
        if texte_du_cv(document):
            flash('CV envoyé et analysé avec succès.', 'success')
        else:
            flash("CV envoyé, mais son texte est illisible (CV scanné ?). Envoyez une version PDF ou DOCX "
                  "créée avec un traitement de texte.", 'danger')
        return redirect(url_for('result', id=document.id))

    return render_template('upload.html')


@app.errorhandler(413)
def file_too_large(error):
    # Le fichier est refuse avant d'etre lu : son nom est inconnu, seule la taille est notee
    return reject_upload('too_large', 'Fichier trop volumineux : 5 Mo maximum.')


@app.route('/history')
@login_required
def history():
    documents = (Document.query.filter_by(user_id=current_user.id)
                 .order_by(Document.upload_date.desc()).all())
    return render_template('history.html', documents=documents)


@app.route('/result/<int:id>')
@login_required
def result(id):
    document = document_du_user(id)
    texte_du_cv(document)
    return render_template('result.html', document=document, analyse=STATUT_ANALYSE)


@app.route('/recherche/<int:id>')
@login_required
def recherche(id):
    """Bouton "Rechercher" : offres les plus proches du CV (matching TF-IDF)."""
    document = document_du_user(id)
    texte = texte_du_cv(document)
    resultats = rechercher(texte) if texte else []
    log_event('RECHERCHE', cv=document.id, resultats=len(resultats))
    return render_template('offres.html', document=document, resultats=resultats)


@app.route('/offre/<int:offre_id>/cv/<int:id>')
@login_required
def offre(offre_id, id):
    """Detail d'une offre, avec l'assistante DRH a cote."""
    return render_template('offre.html', offre=db.get_or_404(Offre, offre_id), document=document_du_user(id),
                           assistante=ASSISTANTE_ACTIVE)


@app.route('/entretien/<int:offre_id>/cv/<int:id>', methods=['POST'])
@login_required
def entretien(offre_id, id):
    """Simulation d'entretien. Le navigateur envoie la conversation deja ecoulee (questions et reponses) :
    vide -> analyse du CV et premiere question ; sinon -> commentaire et question suivante."""
    if not ASSISTANTE_ACTIVE:
        return jsonify(erreur="L'assistante DRH n'est pas encore disponible."), 404
    offre = db.get_or_404(Offre, offre_id)
    texte = texte_du_cv(document_du_user(id))
    historique = (request.get_json(silent=True) or {}).get('historique', [])
    if not texte:
        return jsonify(erreur='Le texte de ce CV est illisible : envoyez une autre version.'), 400
    if not isinstance(historique, list) or not all(isinstance(m, str) for m in historique):
        return jsonify(erreur='Conversation invalide.'), 400
    try:
        if historique:
            reponse = question_suivante(texte, offre, historique)
        else:
            reponse = analyser_candidature(texte, offre)
    except IAIndisponible as erreur:
        log_event('IA_ERREUR', cv=id, offre=offre_id, cause=repr(erreur.__cause__))
        return jsonify(erreur=str(erreur)), 503
    log_event('ENTRETIEN', cv=id, offre=offre_id, etape=len(historique) // 2)
    return jsonify(reponse)
