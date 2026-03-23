import os
import sqlite3 as sql

parrent_dir = os.path.abspath(os.path.dirname(__file__))
base_dir = os.path.abspath(os.path.join(parrent_dir, '..'))
db = os.path.join(base_dir,'instance', 'cvboost.db')

conn = sql.connect(db)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nom varchar(255),
email varchar(255),
password varchar(255))
''')