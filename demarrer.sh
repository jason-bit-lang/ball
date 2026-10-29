#!/bin/sh
# Demarrage sur Render (et dans l'image Docker) : un seul service fait tourner les deux programmes.
# 1. L'API du pitch (FastAPI), joignable seulement depuis la machine elle-meme (127.0.0.1:8000).
uvicorn api_service.main:app --host 127.0.0.1 --port 8000 &

# 2. Le site (Flask avec gunicorn), ouvert au public sur le port donne par Render ($PORT).
# Un seul processus avec 4 fils : un pitch (environ 4 s) ne bloque pas les autres visiteurs
# et la memoire reste sous la limite de l'offre gratuite (512 Mo).
exec gunicorn run:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 30 --access-logfile -
