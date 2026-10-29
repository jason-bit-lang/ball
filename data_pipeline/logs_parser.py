"""Etape 1 : lit le journal du site, detecte les tentatives de fraude et charge le tout dans analytics.db.

C'est un petit pipeline ETL en trois temps (sections ci-dessous) :
- Extraction : lire le fichier logs/evenements.log ecrit par le site (app_web/journal.py) ;
- Transformation : reperer les comportements suspects (faux fichiers, connexions en rafale...) ;
- Chargement : ecrire evenements et alertes dans analytics.db, ou kpi.py fait ses calculs.

Lancement : python -m data_pipeline.logs_parser
"""
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from .config import ANALYTICS_DB, LOG_FILE, RAFALE_MINUTES, RAFALE_SEUIL

# Format d'une ligne : "2026-10-26 17:26:01 | UPLOAD_OK | user=3 | ip=127.0.0.1 | file=cv.pdf"
# Trois groupes : la date, le nom de l'evenement en MAJUSCULES, puis les morceaux " | cle=valeur"
LIGNE_REGEX = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| ([A-Z_]+)((?: \| [a-z_]+=[^|]*)*)$')
# Fichier deguise, par exemple "cv.pdf.exe"
DOUBLE_EXTENSION = re.compile(r'\.(pdf|docx?|jpe?g|png|txt)\.\w+$', re.IGNORECASE)

# Informations gardees pour chaque evenement, dans l'ordre des colonnes de la table evenements
COLONNES = ['date', 'evenement', 'user', 'ip', 'email', 'file', 'ext', 'size', 'reason']


# ---------- Extraction : lecture du fichier ----------

def lire_ligne(ligne):
    """Transforme une ligne en dictionnaire, ou None si elle ne respecte pas le format."""
    match = LIGNE_REGEX.match(ligne.strip())
    if not match:
        return None
    date, evenement, reste = match.groups()
    # " | user=3 | ip=1.2.3.4" -> {'user': '3', 'ip': '1.2.3.4'} (split('=', 1) : coupe au premier "=" seulement)
    details = dict(morceau.split('=', 1) for morceau in reste.split(' | ')[1:])
    return {'date': datetime.strptime(date, '%Y-%m-%d %H:%M:%S'), 'evenement': evenement, **details}


def lire_journal(chemin=LOG_FILE):
    """Renvoie la liste des evenements et le nombre de lignes illisibles."""
    evenements, invalides = [], 0
    try:
        # errors='replace' : un caractere abime ne fait pas planter la lecture de tout le journal
        with open(chemin, encoding='utf-8', errors='replace') as fichier:
            for ligne in fichier:
                if not ligne.strip():
                    continue
                evenement = lire_ligne(ligne)
                if evenement:
                    evenements.append(evenement)
                else:
                    invalides += 1  # une ligne au mauvais format peut signaler un journal modifie a la main
    except FileNotFoundError:
        print(f'Journal introuvable : {chemin} (aucune activite enregistree pour le moment)')
    return evenements, invalides


# ---------- Transformation : detection des fraudes ----------

def rafales(evenements, nom_evenement, cle):
    """Trouve les valeurs de `cle` (ip, email, user) qui ont produit RAFALE_SEUIL evenements
    `nom_evenement` en moins de RAFALE_MINUTES minutes."""
    # Regroupe les dates par valeur : {'1.2.3.4': [date1, date2, ...], ...}
    # defaultdict(list) cree une liste vide la premiere fois qu'une valeur apparait
    dates_par_valeur = defaultdict(list)
    for e in evenements:
        if e['evenement'] == nom_evenement and e.get(cle, '-') != '-':
            dates_par_valeur[e[cle]].append(e['date'])

    resultats = []
    for valeur, dates in dates_par_valeur.items():
        dates.sort()
        # Fenetre glissante : on compare chaque date avec celle situee RAFALE_SEUIL - 1 plus loin
        for i in range(len(dates) - RAFALE_SEUIL + 1):
            if dates[i + RAFALE_SEUIL - 1] - dates[i] <= timedelta(minutes=RAFALE_MINUTES):
                resultats.append((dates[i], valeur))
                break  # une alerte par valeur suffit
    return resultats


def detecter_fraudes(evenements, lignes_invalides):
    """Renvoie la liste des alertes (date, type, cible, detail)."""
    alertes = []
    # 1. Fichiers suspects : contenu qui ne correspond pas a l'extension, ou double extension
    for e in evenements:
        if not e['evenement'].startswith('UPLOAD'):
            continue
        if e.get('reason') == 'bad_signature':
            alertes.append((e['date'], 'faux_fichier', f"user {e.get('user')}",
                            f"contenu different de l'extension : {e.get('file')}"))
        if DOUBLE_EXTENSION.search(e.get('file', '')):
            alertes.append((e['date'], 'double_extension', f"user {e.get('user')}", e.get('file')))

    # 2. Rafales : (evenement surveille, information regroupee, type d'alerte, texte de l'alerte)
    regles = [
        ('LOGIN_FAIL', 'ip', 'force_brute_ip', 'echecs de connexion depuis la meme adresse'),
        ('LOGIN_FAIL', 'email', 'force_brute_compte', 'echecs de connexion sur le meme compte'),
        ('UPLOAD_OK', 'user', 'envois_en_rafale', 'CV envoyes par le meme utilisateur'),
        ('UPLOAD_REJECTED', 'user', 'refus_en_rafale', 'envois refuses pour le meme utilisateur'),
    ]
    for nom_evenement, cle, type_alerte, texte in regles:
        for date, valeur in rafales(evenements, nom_evenement, cle):
            alertes.append((date, type_alerte, f'{cle} {valeur}',
                            f'{RAFALE_SEUIL} {texte} en moins de {RAFALE_MINUTES} min'))

    # 3. Lignes illisibles dans le journal : quelqu'un l'a peut-etre modifie
    if lignes_invalides:
        alertes.append((datetime.now(), 'journal_modifie', 'fichier de logs',
                        f'{lignes_invalides} ligne(s) au mauvais format'))
    return sorted(alertes)  # triees par date (premier element de chaque alerte)


# ---------- Chargement : ecriture dans analytics.db ----------

def charger(evenements, alertes, chemin_db=ANALYTICS_DB):
    """Recree les tables a chaque lancement : le journal reste la source de verite.
    Plus simple et plus sur que de chercher quelles lignes sont nouvelles depuis le dernier lancement."""
    with sqlite3.connect(chemin_db) as conn:
        conn.executescript('''
            DROP TABLE IF EXISTS evenements;
            DROP TABLE IF EXISTS alertes;
            CREATE TABLE evenements (
                id INTEGER PRIMARY KEY, date TEXT, evenement TEXT, user_id TEXT, ip TEXT,
                email TEXT, fichier TEXT, extension TEXT, taille INTEGER, raison TEXT);
            CREATE TABLE alertes (
                id INTEGER PRIMARY KEY, date TEXT, type TEXT, cible TEXT, detail TEXT);
        ''')
        # executemany insere toutes les lignes d'un coup. Les "?" sont remplaces par les valeurs,
        # envoyees a part : un nom de fichier piege ne peut pas modifier la requete (injection SQL).
        conn.executemany(
            'INSERT INTO evenements (date, evenement, user_id, ip, email, fichier, extension, taille, raison) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [[str(e.get(col)) if col == 'date' else e.get(col) for col in COLONNES] for e in evenements])
        conn.executemany('INSERT INTO alertes (date, type, cible, detail) VALUES (?, ?, ?, ?)',
                         [(str(d), t, c, detail) for d, t, c, detail in alertes])


def main():
    """Les trois etapes de l'ETL, puis un resume des alertes dans le terminal."""
    evenements, invalides = lire_journal()
    alertes = detecter_fraudes(evenements, invalides)
    charger(evenements, alertes)
    print(f'{len(evenements)} evenements lus, {invalides} ligne(s) invalide(s), {len(alertes)} alerte(s).')
    for date, type_alerte, cible, detail in alertes:
        print(f'  [{type_alerte}] {date:%d/%m %H:%M} {cible} : {detail}')
    print(f'Base mise a jour : {ANALYTICS_DB}')


if __name__ == '__main__':
    main()
