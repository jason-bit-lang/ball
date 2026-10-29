"""Etape 2 : statistiques d'usage calculees en SQL sur analytics.db.

Pourquoi SQL ? La base analytique est separee de celle du site : on peut y faire des calculs lourds
(regroupements, moyennes) sans jamais ralentir le site.

Lancement : python -m data_pipeline.kpi   (apres python -m data_pipeline.logs_parser)
"""
import sqlite3
from .config import ANALYTICS_DB

# Chaque indicateur est une requete SQL. HAVING filtre APRES le regroupement (GROUP BY),
# alors que WHERE filtre les lignes AVANT.
KPI = {
    "Evenements par type": '''
        SELECT evenement, COUNT(*) AS nombre
        FROM evenements GROUP BY evenement ORDER BY nombre DESC''',

    "Envois de CV par jour": '''
        SELECT DATE(date) AS jour,
               SUM(evenement = 'UPLOAD_OK') AS reussis,
               SUM(evenement = 'UPLOAD_REJECTED') AS refuses
        FROM evenements WHERE evenement LIKE 'UPLOAD%'
        GROUP BY jour ORDER BY jour''',

    "Taux de refus par extension (%)": '''
        SELECT COALESCE(NULLIF(extension, ''), 'inconnue') AS extension, COUNT(*) AS envois,
               ROUND(100.0 * SUM(evenement = 'UPLOAD_REJECTED') / COUNT(*), 1) AS taux_refus
        FROM evenements WHERE evenement LIKE 'UPLOAD%'
        GROUP BY 1 ORDER BY envois DESC''',

    "Raisons de refus": '''
        SELECT raison, COUNT(*) AS nombre
        FROM evenements WHERE evenement = 'UPLOAD_REJECTED'
        GROUP BY raison ORDER BY nombre DESC''',

    "Taille moyenne des CV acceptes (Ko)": '''
        SELECT extension, COUNT(*) AS cv, ROUND(AVG(taille) / 1024.0, 1) AS taille_moyenne_ko
        FROM evenements WHERE evenement = 'UPLOAD_OK'
        GROUP BY extension''',

    "Utilisateurs ayant envoye au moins 2 CV": '''
        SELECT user_id, COUNT(*) AS cv_envoyes, MAX(date) AS dernier_envoi
        FROM evenements WHERE evenement = 'UPLOAD_OK'
        GROUP BY user_id HAVING COUNT(*) >= 2 ORDER BY cv_envoyes DESC''',

    "Adresses IP avec au moins 3 echecs de connexion": '''
        SELECT ip, COUNT(*) AS echecs, COUNT(DISTINCT email) AS comptes_vises
        FROM evenements WHERE evenement = 'LOGIN_FAIL'
        GROUP BY ip HAVING COUNT(*) >= 3 ORDER BY echecs DESC''',

    "Taux de reussite des connexions par jour (%)": '''
        SELECT DATE(date) AS jour, COUNT(*) AS tentatives,
               ROUND(100.0 * SUM(evenement = 'LOGIN_OK') / COUNT(*), 1) AS taux_reussite
        FROM evenements WHERE evenement IN ('LOGIN_OK', 'LOGIN_FAIL')
        GROUP BY jour ORDER BY jour''',

    "Alertes de fraude par type": '''
        SELECT type, COUNT(*) AS nombre FROM alertes GROUP BY type ORDER BY nombre DESC''',
}


def calculer_kpi(chemin_db=ANALYTICS_DB):
    """Renvoie {titre: (colonnes, lignes)} pour chaque indicateur."""
    resultats = {}
    with sqlite3.connect(chemin_db) as conn:  # "with" ferme la base tout seul a la fin
        for titre, requete in KPI.items():
            curseur = conn.execute(requete)
            colonnes = [c[0] for c in curseur.description]  # noms des colonnes du resultat
            resultats[titre] = (colonnes, curseur.fetchall())
    return resultats


def afficher_tableau(colonnes, lignes):
    """Affiche un resultat en colonnes alignees dans le terminal."""
    # Largeur de chaque colonne : la plus longue valeur de la colonne (titre compris)
    largeurs = [max(len(str(v)) for v in [col] + [l[i] for l in lignes]) for i, col in enumerate(colonnes)]
    for ligne in [colonnes] + lignes:
        print('  ' + ' | '.join(str(v).ljust(w) for v, w in zip(ligne, largeurs)))


def main():
    """Calcule puis affiche chaque indicateur."""
    for titre, (colonnes, lignes) in calculer_kpi().items():
        print(f'\n{titre}')
        if lignes:
            afficher_tableau(colonnes, lignes)
        else:
            print('  (aucune donnee)')


if __name__ == '__main__':
    main()
