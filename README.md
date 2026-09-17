# OmniVente

**Vendez sur WhatsApp, Instagram, Messenger et e-mail depuis un seul tableau de bord.**
Projet Hackathon LSC 2026 — commerçant témoin : *Tinos TechLogistics* (Lomé, Togo).

L'agent conversationnel guide le client par **numéros à choix simples** (1, 2, 3…), vérifie le
stock, convient d'un créneau, récupère la position GPS, puis **crée automatiquement la commande**
dans le tableau de bord du commerçant.

---

## 1. Arborescence

```
omnivente/
├── README.md
├── LOCAL_SETUP.md               Installation et lancement sur la machine locale
├── frontend/                   Tableau de bord statique, aucun build requis
│   ├── index.html              Tableau de bord : connecté à l'API si config.js est renseigné,
│   │                           repli automatique en mode démonstration sinon
│   └── config.js               Adresse de l'API locale
└── backend/
    ├── requirements.txt
    ├── .env.example
    ├── data/
    │   └── products.csv        Catalogue officiel du Hackathon (8 références)
    ├── scripts/
    │   ├── init_db.sql         Création de la base, de l'utilisateur et des 5 tables
   │   └── seed.py             Import du CSV + jeu de démonstration
    └── app/
        ├── main.py             Application FastAPI, sondage e-mail démarré au lancement
      ├── config.py           Variables d'environnement locales
        ├── database.py         Moteur SQLAlchemy et session
        ├── deps.py             Résolution du commerçant : par en-tête (tableau de bord)
        │                       ou par slug d'URL (webhooks, qui n'envoient pas d'en-tête)
        ├── models.py           tenants · products · clients · orders · messages
        ├── schemas.py          Contrats Pydantic de l'API
        ├── routers/
        │   ├── tenants.py      Profil de l'entreprise
        │   ├── products.py     Catalogue et stock
        │   ├── orders.py       Commandes, vue par statut, changement d'étape
        │   ├── clients.py      Répertoire clients
        │   ├── conversations.py Orchestration du dialogue et création des commandes
        │   ├── stats.py        Indicateurs du tableau de bord
        │   └── webhooks.py     WhatsApp Cloud API, Meta Graph, relais e-mail
        └── services/
            ├── groq_client.py  Compréhension du langage naturel (llama-3.3-70b-versatile)
            ├── state_machine.py Parcours de vente en 6 étapes
            ├── channels.py     Envoi des réponses sur chaque canal
            └── mail_poller.py  Sondage IMAP (pas de webhook Gmail gratuit)
```

Pour installer et lancer le projet en local, suivez **[LOCAL_SETUP.md](LOCAL_SETUP.md)**.

---

## 2. Démarrage en 5 minutes

### 2.1 Prérequis

- Python 3.11 ou plus récent
- PostgreSQL 14 ou plus récent
- Une clé Groq gratuite : <https://console.groq.com/keys>

### 2.2 Base de données PostgreSQL

Le script crée l'utilisateur, la base, les cinq tables, le commerçant témoin et le catalogue.

```bash
cd backend
sudo -u postgres psql -f scripts/init_db.sql
```

Sous Windows (pgAdmin ou psql) :

```bash
psql -U postgres -f scripts/init_db.sql
```

Équivalent manuel, si vous préférez tout piloter à la main :

```sql
CREATE ROLE omnivente WITH LOGIN PASSWORD 'change_me_2026';
CREATE DATABASE omnivente_db OWNER omnivente ENCODING 'UTF8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE omnivente_db TO omnivente;
```

Vérification :

```bash
psql -U omnivente -d omnivente_db -c "\dt"
psql -U omnivente -d omnivente_db -c "SELECT position, ref, name, price, in_stock FROM products ORDER BY position;"
```

### 2.3 Environnement Python

Sous Fedora, utilisez Python 3.13 : les dépendances actuelles du projet ne compilent
pas correctement avec Python 3.14. Installez d'abord les outils système :

```bash
sudo dnf install -y python3.13-devel postgresql-devel gcc
```

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Si Fedora tente de compiler `psycopg2-binary==2.9.9`, installez la version
compatible dans l'environnement local :

```bash
pip install psycopg2-binary==2.9.10
```

### 2.4 Clé d'API Groq

Ouvrez `.env` et renseignez la clé récupérée sur la console Groq :

```
GROQ_API_KEY=gsk_votre_cle_ici
GROQ_MODEL=llama-3.3-70b-versatile
```

Sans clé, l'agent continue de fonctionner : la machine d'état gère seule les réponses
numériques. Avec la clé, il comprend en plus le langage naturel (« j'en veux deux »,
« vous êtes ouverts dimanche ? »).

### 2.5 Données et lancement

```bash
python -m scripts.seed --demo      # tables + catalogue CSV + jeu de démonstration
uvicorn app.main:app --reload
```

Avec la configuration locale Fedora déjà préparée dans `.env`, la commande robuste
depuis n'importe quel dossier est :

```bash
/chemin/vers/backend/.venv/bin/uvicorn app.main:app \
   --app-dir /chemin/vers/backend \
   --env-file /chemin/vers/backend/.env \
   --host 127.0.0.1 --port 8000
```

- API : <http://localhost:8000>
- Documentation interactive : <http://localhost:8000/docs>
- État du service : <http://localhost:8000/health>

### 2.6 Interface

Ouvrez `frontend/index.html` dans un navigateur : elle fonctionne immédiatement,
sans serveur, en mode démonstration (bandeau ambre en haut de l'écran).

Pour la brancher sur l'API locale que vous venez de lancer, vérifiez
`frontend/config.js` :

```js
window.OMNIVENTE_API_BASE = "http://localhost:8000/api";
window.OMNIVENTE_TENANT = "kino-steak";
```

Rechargez la page : le bandeau passe au vert **Connecté à l'API**.

Dans l'onglet **Commandes**, le sélecteur de chaque commande permet de la déplacer
entre « À préparer », « En cours de livraison », « Retrait en boutique », « Terminé »
et « Annulé / Problème ». Le changement est enregistré par `PATCH /api/orders/{reference}`.

---

## 3. Schéma des tables

| Table | Rôle | Colonnes principales |
|---|---|---|
| `tenants` | Le commerçant abonné | `slug`, `company`, `pickup_point`, `delivery_zone`, `integrations` (JSONB) |
| `products` | Catalogue | `ref`, `position` (le numéro tapé par le client), `price`, `quantity`, `in_stock` |
| `clients` | Contacts, tous canaux | `channel`, `external_id`, `phone`, `location`, `session_state` (JSONB) |
| `orders` | Commandes | `reference`, `quantity`, `amount`, `status`, `fulfilment`, `slot`, `place` |
| `messages` | Historique des échanges | `direction` (`in`/`out`), `body`, `step` |

`clients.session_state` porte l'état du dialogue en cours : étape, article choisi, quantité,
mode de retrait, créneau, position. Une conversation interrompue reprend donc exactement
là où elle s'était arrêtée, même après un redémarrage du serveur.

Statuts de commande : `preparer`, `livraison`, `retrait`, `termine`, `probleme`.

---

## 4. Parcours de vente

```
Étape 1  catalogue   → « 1 - Pack Basic (10 000 FCFA) … Répondez par le numéro de votre choix. »
Étape 2  quantite    → « Combien d'exemplaires souhaitez-vous ? »
Étape 3  stock       → si l'article est épuisé, l'agent propose les alternatives disponibles
Étape 4  mode        → « 1 - Livraison à domicile   2 - Retrait en boutique »
Étape 5a retrait     → jour et heure de passage en boutique
Étape 5b livraison   → jour et heure, puis position GPS
Étape 6  validation  → récapitulatif, confirmation, création de la commande
```

Toute la logique tient dans `app/services/state_machine.py`, sans dépendance à la base :
elle est donc testable seule et se comporte de façon identique sur les quatre canaux.
Le stock est décrémenté à la confirmation, et le client est créé s'il est inconnu.

---

## 5. Points d'entrée de l'API

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/chat` | Message entrant → réponse de l'agent (utilisé par le simulateur) |
| `GET` | `/api/conversations` | Fils de discussion, avec l'étape en cours |
| `GET` | `/api/conversations/{id}/messages` | Historique d'une conversation |
| `GET` | `/api/products` | Catalogue |
| `PATCH` | `/api/products/{ref}/stock` | Mise à jour du stock |
| `GET` | `/api/orders/board` | Commandes regroupées par statut |
| `PATCH` | `/api/orders/{reference}` | Changement d'étape d'une commande |
| `GET` | `/api/clients` | Répertoire clients |
| `GET` | `/api/tenant` · `PUT` | Profil de l'entreprise |
| `GET` | `/api/stats` | Indicateurs du tableau de bord |

Exemple de vente complète en ligne de commande :

```bash
API=http://localhost:8000/api
post () { curl -s -X POST $API/chat -H 'Content-Type: application/json' \
  -d "{\"channel\":\"whatsapp\",\"external_id\":\"22890773164\",\"name\":\"Délali Amouzou\",\"text\":\"$1\"}" \
  | python -m json.tool; }

post "bonjour"                       # salutation + catalogue numéroté
post "2"                             # Pack Pro
post "2"                             # quantité
post "1"                             # livraison
post "jeudi 18 septembre à 14h00"    # créneau
post "6.1319, 1.2492"                # position GPS
post "1"                             # confirmation → la commande apparaît dans /api/orders/board
```

---

## 6. Connexion des canaux

### WhatsApp Business (API Cloud Meta)

1. Créez une application sur <https://developers.facebook.com> et ajoutez le produit *WhatsApp*.
2. Relevez le **Phone Number ID** et le **jeton d'accès**, puis reportez-les dans `.env`.
3. Exposez votre serveur local : `ngrok http 8000`.
4. Dans *WhatsApp → Configuration*, déclarez l'URL de rappel
   `https://votre-domaine.ngrok.app/webhooks/whatsapp/kino-steak`
   et le jeton de vérification `omnivente_kino_2026`.
5. Abonnez-vous au champ `messages`. Meta appelle l'URL en `GET` pour la vérifier,
   puis livre chaque message en `POST`.

### Instagram et Messenger (API Graph)

Même application Meta, produit *Messenger*. Autorisations nécessaires :
`pages_messaging`, `pages_manage_metadata`, `instagram_basic`, `instagram_manage_messages`.
URL de rappel : `https://votre-domaine.ngrok.app/webhooks/meta/kino-steak`.
Le bouton « Se connecter avec Facebook » de la page *Canaux connectés* déclenche
l'autorisation OAuth et enregistre le jeton de page.

### E-mail de vente

Renseignez SMTP/IMAP dans `.env`. Pour Gmail, activez la validation en deux étapes puis
générez un **mot de passe d'application** — jamais votre mot de passe habituel.
Un relais IMAP (ou un service de réception comme Mailgun) poste les messages sur
`/webhooks/email/kino-steak`.

---

## 7. Déroulé conseillé pour la soutenance

Quand le backend local est lancé, montrez le vrai parcours :

1. **Tableau de bord** — badge vert « Connecté à l'API » en haut à droite.
   Indicateurs, courbe des messages par canal, répartition des ventes.
2. **WhatsApp réel** — depuis votre téléphone, écrivez au numéro de test :
   `bonjour` → `2` → `2` → `1` → `jeudi 18 septembre à 14h00` → position GPS → `1`.
3. **Retournez sur Commandes** (onglet du tableau de bord, pas besoin de
   recharger) — la commande apparaît dans « À préparer » en quelques secondes,
   le stock du catalogue a été décrémenté.
4. **Cas de rupture** — recommencez et tapez `3` (Pack Entreprise) : l'agent
   signale la rupture et propose immédiatement des alternatives.
5. **E-mail** — envoyez un message à l'adresse de vente, montrez la réponse
   automatique arriver (20-30 s, le temps du sondage IMAP).
6. **Filet de sécurité** — si le Wi-Fi de la salle bloque WhatsApp ou coupe :
   l'onglet **Conversations → Tester l'agent** envoie de vrais messages à
   l'API sans avoir besoin d'un téléphone. Si même le backend devient
   injoignable, le tableau de bord repasse tout seul en mode démonstration
   (bandeau ambre) : la présentation continue sans écran blanc.

Argument technique à mettre en avant : la machine d'état est **partagée entre
le mode démonstration du front et le backend réel**, ce qui garantit un
parcours identique dans les deux cas, tandis que Groq n'intervient que pour
interpréter le langage naturel — l'IA ne peut donc pas « inventer » une commande.

---

## 8. Dépannage

| Symptôme | Cause probable | Correction |
|---|---|---|
| `could not connect to server` | PostgreSQL arrêté | `sudo service postgresql start` |
| `password authentication failed` | `DATABASE_URL` erroné | Vérifiez l'utilisateur et le mot de passe dans `.env` |
| `relation "tenants" does not exist` | Tables non créées | `python -m scripts.seed` |
| L'agent ignore le langage naturel | Clé Groq absente | Renseignez `GROQ_API_KEY` puis relancez |
| Webhook Meta refusé (403) | Jeton de vérification différent | Alignez `WHATSAPP_VERIFY_TOKEN` et la valeur saisie chez Meta |
| Le navigateur bloque les appels API | CORS | Ajoutez l'origine du front dans `CORS_ORIGINS` |
