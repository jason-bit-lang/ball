
from flask import Flask, render_template, request, redirect, g

app = Flask(__name__)
@app.route('/')
def index():
    current_user = True
    return render_template('index.html', current_user=current_user)

@app.route('/register', methods = ['GET', 'POST'])
def register():
    current_user = True
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        password = request.form['password']
        confirmation_mot_secret = request.form[('confirmation_mot_secret')]
        return redirect("/login")
    return render_template('register.html', current_user=current_user)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    current_user = True
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        return redirect("/") #je redirige à l'acceuil parce que je n'ai pas encore créé l'historique.
    return render_template('login.html', current_user=current_user)


