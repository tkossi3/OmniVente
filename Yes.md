Terminal 1 :
cd /home/tkossi3/Music/OmniVente/backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Terminal 2 :

cd /home/tkossi3/Music/OmniVente/frontend
python3 -m http.server 5173 --bind 127.0.0.1

Puis ouvrir :
```
cd /home/tkossi3/Music/OmniVente
git pull
cd backend
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m scripts.seed
´´´

Interface : http://127.0.0.1:5173
API : http://127.0.0.1:8000
Santé API : http://127.0.0.1:8000/health
Documentation : http://127.0.0.1:8000/docs
Pour mettre à jour le projet :


