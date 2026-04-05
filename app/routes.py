from enum import unique
from flask import Flask, render_template, request, redirect,url_for,flash
import os
import uuid
from flask_login import login_required,current_user,login_user,logout_user
from werkzeug.utils import secure_filename
from .models import Document, User
from . import db,app #importe l'app configurée dans __init__.py
from werkzeug.security import generate_password_hash


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        password = request.form['password']
        confirmation_mot_secret = request.form[('confirmation_mot_secret')]
        if password != confirmation_mot_secret:
            return "les mots de passe ne correspondent pas."

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect("/register")

        new_user = User(
            nom=nom,
            prenom=prenom,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Bravo! Vous êtes maintenant inscrits.", "success")
        return redirect("/login")
    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email') #utilise get pour éviter KeyError
        password = request.form.get('password')
        if not email or not password:
            return "Veuillez inscrire toutes les informations."
        user = User.query.filter_by(email=email).first()
        login_user(user)
        return redirect("/") #je redirige à l'acceuil parce que je n'ai pas encore créé l'historique.
    return render_template('login.html')

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect("/")

ALLOWED_EXTENSIONS = { "pdf", "docx"}
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/upload', methods = ['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('cv')
        if not file or file.filename == '':
            flash('Aucun fichier dawg.')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Fichier invalide dawg: PDF ou DOCX")
            return redirect(request.url)
        if file.filename == '':
            flash("Aucun fichier sélectionné dawg")
            return redirect(request.url)
        if file and allowed_file(file.filename):
             original_filename = secure_filename(file.filename)
             extension = os.path.splitext(original_filename)[1].lower()
             unique_filename = (f"{uuid.uuid4()}.{extension}")
             upload_folder = os.path.join("uploads",unique_filename)
             file.save(upload_folder)
             document = Document(
                 original_filename = original_filename,
                 stored_filename = unique_filename,
                 user_id = current_user.id
             )
             db.session.add(document)
             db.session.commit()
             return redirect('/history')

    return render_template('upload.html')

@app.route('/history')
@login_required
def history():
    user_docs = Document.query.filter_by(user_id = current_user.id).all()
    return render_template('history.html', documents = user_docs)

@app.route("/result/<int:id>")
@login_required
def result(id):
    doc = Document.query.get_or_404(id)
    return render_template('result.html', document = doc)

