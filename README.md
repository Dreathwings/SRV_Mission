# WEB_ordre_mission

## Production

1. Installer les dependances:
   `pip install -r requirements.txt`
2. Copier [D:\SRV_mission\.env.production.example](D:/SRV_mission/.env.production.example) vers un vrai fichier d'environnement ou exporter les variables manuellement.
3. Renseigner au minimum:
   - `MISSION_SECRET_KEY`
   - `MISSION_DB_PASSWORD`
   - `MISSION_CAS_DB_PASSWORD`
   - `MISSION_PUBLIC_BASE_URL` en `https://...`
4. Demarrer en production:
   `bash start.sh`

Le serveur demarre via `gunicorn` sur `wsgi:app`.
