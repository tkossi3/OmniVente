# OmniVente

Commerce conversationnel et billetterie omnicanale pour les PME. Vos clients ecrivent sur
WhatsApp, Instagram, Messenger ou par email ; OmniVente repond, enregistre la commande et
l'affiche dans un tableau de bord en bandes horizontales.

- **Backend** : FastAPI + SQLAlchemy 2.0 (asyncpg) sur **PostgreSQL local reel**
- **Frontend** : React 18 + Vite + Tailwind CSS (mode sombre / clair)
- **Agent de vente** : detection d'intention, machine a etats de vente, RAG FAQ sur vos reponses existantes

---

## 1. Prerequis

| Outil | Version conseillee | Verification |
|---|---|---|
| PostgreSQL | 14 ou superieur | `psql --version` |
| Python | 3.11 ou superieur | `python --version` |
| Node.js | 18 ou superieur | `node --version` |

---

## 2. Creer la base de donnees PostgreSQL locale

Ouvrez un terminal et connectez-vous a PostgreSQL :

```bash
psql -U postgres
```

Puis executez exactement ces quatre commandes SQL :

```sql
CREATE USER omnivente_user WITH PASSWORD 'omnivente_secret_password';
CREATE DATABASE omnivente_db OWNER omnivente_user;
GRANT ALL PRIVILEGES ON DATABASE omnivente_db TO omnivente_user;
\q
```

Sur PostgreSQL 15 et superieur, ajoutez ces deux lignes pour autoriser l'ecriture dans le
schema `public` (sinon la creation des tables echoue) :

```bash
psql -U postgres -d omnivente_db
```

```sql
GRANT ALL ON SCHEMA public TO omnivente_user;
ALTER SCHEMA public OWNER TO omnivente_user;
\q
```

Verifiez la connexion avec le nouvel utilisateur :

```bash
psql -U omnivente_user -d omnivente_db -h localhost -c "SELECT current_database(), current_user;"
```

**Windows** : si `psql` n'est pas reconnu, utilisez le chemin complet, par exemple
`"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres`.

---

## 3. Lancer le backend

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env        # Windows : copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Au demarrage, FastAPI se connecte a `omnivente_db` et cree toutes les tables manquantes
(`Base.metadata.create_all`). Verifiez :

- API en ligne : http://127.0.0.1:8000
- Etat de la base : http://127.0.0.1:8000/health → `{"database": "connectee", "status": "ok"}`
- Documentation interactive : http://127.0.0.1:8000/docs

Tables creees : `tenants`, `customers`, `products`, `orders`, `order_items`, `messages`, `faq_entries`.

---

## 4. Charger les donnees de test (Entreprise D)

Le script lit les 4 fichiers CSV de `backend/data/` et les insere dans PostgreSQL :

```bash
cd backend
python -m scripts.seed_db --reset
```

Options :

```bash
python -m scripts.seed_db                      # ingestion sans vider les tables
python -m scripts.seed_db --data-dir /chemin   # utiliser vos propres CSV
```

Fichiers attendus dans le dossier de donnees :

- `04_Demandes_Clients_clients.csv`
- `04_Demandes_Clients_messages.csv`
- `04_Demandes_Clients_produits.csv`
- `04_Demandes_Clients_reponses_existantes.csv`

Le script tolere des intitules de colonnes differents (alias definis dans `ALIASES`) et les
separateurs `,` `;` ou tabulation. Si vous avez vos propres exports, remplacez simplement les
fichiers du dossier `backend/data/`.

Identifiants crees :

```
Email        : contact@entreprise-d.tg
Mot de passe : omnivente2026
```

Verifiez l'ingestion directement en base :

```bash
psql -U omnivente_user -d omnivente_db -h localhost -c "SELECT count(*) FROM products;"
```

---

## 5. Lancer le frontend

Dans un second terminal :

```bash
cd frontend
npm install
npm run dev
```

Ouvrez http://localhost:5173. Vite relaie les appels `/api` vers `http://127.0.0.1:8000`
(voir `vite.config.js`), il n'y a donc rien a configurer pour le developpement local.

---

## 6. Carte d'edition du code

Ce que vous voudrez modifier en premier, et ou le faire.

### Identite visuelle

| Modification | Fichier | Repere precis |
|---|---|---|
| Palette complete (brand, ink, paper, saffron) | `frontend/tailwind.config.js` | objet `theme.extend.colors` |
| Couleurs des badges de statut | `frontend/src/components/constants.js` | tableau `ORDER_STATUSES`, cles `badge`, `dot`, `accent` |
| Couleurs et fonds par canal | `frontend/src/components/constants.js` | objet `CHANNELS`, cles `color`, `surface`, `bubble` |
| Motifs de fond des chatbox | `frontend/src/index.css` | classes `.chat-whatsapp`, `.chat-instagram`, `.chat-messenger`, `.chat-email` |
| Logo OEV (forme, degrade, monogramme) | `frontend/src/components/LogoOEV.jsx` | `<path>` de la bulle, `<text>` du monogramme |
| Polices | `frontend/index.html` + `tailwind.config.js` | balise Google Fonts + `fontFamily` |
| Styles de boutons, champs, cartes | `frontend/src/index.css` | bloc `@layer components` |
| Apparence du toggle sombre / clair | `frontend/src/components/ThemeToggle.jsx` | classes de translation du curseur |

### Navigation et pages

| Modification | Fichier | Repere precis |
|---|---|---|
| Entrees du menu lateral | `frontend/src/components/Sidebar.jsx` | tableau `NAV` |
| Position du profil entreprise | `frontend/src/components/Sidebar.jsx` | bloc `NavLink to="/profil"` (au-dessus du bouton de deconnexion) |
| Routes de l'application | `frontend/src/App.jsx` | composant `<Routes>` |
| Champs du formulaire d'inscription | `frontend/src/pages/Register.jsx` | constante `EMPTY` + champs du `<form>` |
| Liste des secteurs d'activite | `frontend/src/components/constants.js` (UI) et `backend/app/models/enums.py` (validation) | `SECTORS` / `class Sector` |
| Largeur des cartes de commande | `frontend/src/components/OrderSwimlane.jsx` | classe `w-[272px]` |

### Logique metier et IA

| Modification | Fichier | Repere precis |
|---|---|---|
| Mots-cles de detection d'intention | `backend/app/services/bot_ai.py` | dictionnaire `INTENT_KEYWORDS` |
| Textes des reponses du vendeur virtuel | `backend/app/services/bot_ai.py` | methode `_compose_reply` |
| Etapes de vente et transitions | `backend/app/services/sales_state_machine.py` | `TRANSITIONS` et `STAGE_GOALS` |
| Seuil de declenchement des reponses FAQ | `backend/app/services/rag_faq.py` | parametre `threshold` de `best_answer` (0.18) |
| Mots vides du moteur de recherche | `backend/app/services/rag_faq.py` | ensemble `STOPWORDS` |
| Creation automatique de commande | `backend/app/api/messages.py` | bloc `if decision.should_create_order` |
| Statuts de commande disponibles | `backend/app/models/enums.py` | `class OrderStatus` + `ORDER_STATUS_LABELS` |

### Base de donnees et securite

| Modification | Fichier | Repere precis |
|---|---|---|
| Identifiants PostgreSQL | `backend/.env` | `DATABASE_URL` |
| Taille du pool de connexions | `backend/app/core/database.py` | `create_async_engine(pool_size=10, max_overflow=20)` |
| Creation automatique des tables | `backend/app/core/database.py` | `init_models()` → `run_sync(Base.metadata.create_all)` |
| Cle secrete et duree de session JWT | `backend/.env` | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Origines CORS autorisees | `backend/.env` | `CORS_ORIGINS` |
| Schema des tables | `backend/app/models/*.py` | classes SQLAlchemy |
| Cles d'API des canaux | `backend/.env` | section WhatsApp / Meta / SMTP |

---

## 7. Structure du projet

```
omnivente/
├── backend/
│   ├── app/
│   │   ├── api/          auth.py, products.py, orders.py, messages.py, webhooks.py, deps.py
│   │   ├── core/         config.py, database.py, security.py
│   │   ├── models/       tenant, customer, product, order, message, faq, enums
│   │   ├── schemas/      schemas Pydantic
│   │   ├── services/     bot_ai.py, sales_state_machine.py, rag_faq.py, channels.py
│   │   └── main.py
│   ├── data/             les 4 fichiers CSV d'Entreprise D
│   ├── scripts/seed_db.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/   LogoOEV, Sidebar, Layout, ThemeToggle, OrderSwimlane, ChatBox, StatusBadge, constants
│   │   ├── pages/        Register, Login, Dashboard, Orders, Inbox, Products, Profile
│   │   ├── context/      AuthContext, ThemeContext
│   │   ├── api/client.js
│   │   └── App.jsx
│   ├── package.json
│   └── tailwind.config.js
├── README.md
└── GUIDE_CONFIGURATION_CANAUX.md
```

---

## 8. Principaux endpoints

| Methode | Route | Role |
|---|---|---|
| POST | `/api/auth/register` | Inscription d'une entreprise |
| POST | `/api/auth/login` | Connexion, retourne un JWT |
| GET / PATCH | `/api/auth/me` | Profil de l'entreprise |
| GET / POST | `/api/products` | Catalogue |
| GET | `/api/orders/swimlanes` | Commandes groupees par bande de statut |
| GET | `/api/orders/stats` | Indicateurs du tableau de bord |
| PATCH | `/api/orders/{id}/status` | Changer le statut d'une commande |
| GET | `/api/conversations` | Liste des conversations |
| POST | `/api/messages` | Reponse manuelle d'un agent |
| POST | `/api/messages/incoming` | Simuler un message client (teste l'agent) |
| POST | `/api/webhooks/whatsapp/{tenant_id}` | Reception WhatsApp Cloud API |
| POST | `/api/webhooks/meta/{tenant_id}` | Reception Messenger et Instagram |

---

## 9. Depannage

| Message | Cause probable | Solution |
|---|---|---|
| `connection refused ... 5432` | PostgreSQL n'est pas demarre | `sudo service postgresql start` ou lancez le service Windows |
| `password authentication failed` | Mot de passe different de `.env` | Reexecutez `ALTER USER omnivente_user WITH PASSWORD '…';` |
| `permission denied for schema public` | PostgreSQL 15+ | Appliquez les deux commandes `GRANT ALL ON SCHEMA public` de l'etape 2 |
| `ModuleNotFoundError: app` | Lance depuis le mauvais dossier | Placez-vous dans `backend/` avant `uvicorn` |
| `InterfaceError: cannot perform operation` | `greenlet` manquant | `pip install greenlet` |
| Page blanche sur le frontend | Backend eteint | Verifiez http://127.0.0.1:8000/health |
| 401 sur toutes les requetes | Session expiree | Reconnectez-vous ; ajustez `ACCESS_TOKEN_EXPIRE_MINUTES` |

Pour brancher vos comptes WhatsApp, Instagram, Messenger et votre email professionnel,
poursuivez avec **GUIDE_CONFIGURATION_CANAUX.md**.
