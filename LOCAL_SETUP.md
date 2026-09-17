# Installation locale OmniVente

## Prerequis

- Python 3.11 ou plus recent
- PostgreSQL 14 ou plus recent
- Node.js est optionnel : le frontend est un fichier statique

## 1. Creer la base PostgreSQL

Depuis le dossier `backend` :

```bash
sudo -u postgres psql -f scripts/init_db.sql
```

La base utilise par defaut :

```text
postgresql+psycopg2://omnivente:change_me_2026@localhost:5432/omnivente_db
```

Adaptez `DATABASE_URL` dans `.env` si votre PostgreSQL utilise d'autres identifiants.

## 2. Installer le backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Dans `.env`, gardez au minimum :

```env
DATABASE_URL=postgresql+psycopg2://omnivente:change_me_2026@localhost:5432/omnivente_db
APP_ENV=development
DEFAULT_TENANT=kino-steak
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
AUTO_SEED=true
AUTO_SEED_DEMO=true
```

Ajoutez `GROQ_API_KEY` si vous voulez la comprehension du langage naturel. Sans cette cle, le parcours numerique et l'escalade vendeur restent disponibles.

## 3. Initialiser les donnees

```bash
cd backend
.venv/bin/python -m scripts.seed --demo
```

L'operation est idempotente : vous pouvez la relancer sans creer de doublons.

## 4. Lancer le backend

Terminal 1 :

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verification :

- API : http://127.0.0.1:8000
- Documentation : http://127.0.0.1:8000/docs
- Etat : http://127.0.0.1:8000/health

## 5. Lancer le frontend

Terminal 2 :

```bash
cd frontend
python3 -m http.server 5173 --bind 127.0.0.1
```

Ouvrez ensuite http://127.0.0.1:5173.

Le fichier `frontend/config.js` pointe deja vers :

```js
window.OMNIVENTE_API_BASE = "http://127.0.0.1:8000/api";
window.OMNIVENTE_TENANT = "kino-steak";
```

Le tableau de bord affiche le mode connecte quand l'API repond. Sinon, il bascule en mode demonstration hors ligne.

## Arret

Dans chaque terminal, appuyez sur `Ctrl+C`.

## Depannage rapide

- `Address already in use` : un service tourne deja sur le port 8000 ou 5173. Utilisez-le ou arretez-le avec `Ctrl+C` dans son terminal.
- Erreur PostgreSQL : verifiez que le service PostgreSQL est demarre et que `DATABASE_URL` correspond a votre installation.
- Frontend en mode demonstration : verifiez http://127.0.0.1:8000/health puis rechargez la page.
