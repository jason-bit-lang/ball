import os
import re
import uuid
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from . import app, db
from .models import Document, User

# Extensions acceptees et premiers octets attendus pour chacune
# (un PDF commence par %PDF, un DOCX est une archive zip qui commence par PK)
SIGNATURES = {'pdf': b'%PDF', 'docx': b'PK\x03\x04'}
EMAIL_REGEX = r'[^@\s]+@[^@\s]+\.[^@\s]+'
PASSWORD_MIN_LENGTH = 8


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


def is_valid_cv(file):
    """Verifie l'extension ET le vrai contenu du fichier."""
    signature = SIGNATURES.get(file_extension(file.filename))
    if signature is None:
        return False
    debut = file.stream.read(len(signature))
    file.stream.seek(0)  # remet la lecture au debut pour pouvoir enregistrer le fichier
    return debut == signature


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
            flash('Email ou mot de passe incorrect.', 'danger')
            return render_template('login.html', email=email)

        login_user(user)
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
            flash('Aucun fichier sélectionné.', 'danger')
            return redirect(url_for('upload'))
        if not is_valid_cv(file):
            flash('Fichier invalide : seuls les vrais fichiers PDF ou DOCX sont acceptés.', 'danger')
            return redirect(url_for('upload'))

        # Le fichier est renomme avec un identifiant unique (UUID) :
        # deux CV portant le meme nom ne s'ecrasent jamais
        original_filename = secure_filename(file.filename)
        stored_filename = f'{uuid.uuid4()}.{file_extension(original_filename)}'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_filename))

        document = Document(original_filename=original_filename,
                            stored_filename=stored_filename,
                            user_id=current_user.id)
        db.session.add(document)
        db.session.commit()
        flash('CV envoyé avec succès.', 'success')
        return redirect(url_for('history'))

    return render_template('upload.html')


@app.errorhandler(413)
def file_too_large(error):
    flash('Fichier trop volumineux : 5 Mo maximum.', 'danger')
    return redirect(url_for('upload'))


@app.route('/history')
@login_required
def history():
    documents = (Document.query.filter_by(user_id=current_user.id)
                 .order_by(Document.upload_date.desc()).all())
    return render_template('history.html', documents=documents)


@app.route('/result/<int:id>')
@login_required
def result(id):
    # Un utilisateur ne peut ouvrir que ses propres documents
    document = Document.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('result.html', document=document)
