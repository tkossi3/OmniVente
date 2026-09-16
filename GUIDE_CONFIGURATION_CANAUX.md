# Connecter vos canaux de vente

Ce guide couvre WhatsApp Business, l'email professionnel, Facebook Messenger et Instagram
Direct. Chaque section se termine par les variables a remplir dans `backend/.env`.

Apres chaque modification du fichier `.env`, redemarrez le serveur FastAPI.

---

## 0. Exposer votre serveur local

Meta ne peut pas appeler `localhost`. Ouvrez un tunnel public avant de configurer les webhooks :

```bash
# Option 1 : ngrok
ngrok http 8000

# Option 2 : cloudflared
cloudflared tunnel --url http://localhost:8000
```

Vous obtenez une URL du type `https://abcd-12-34-56.ngrok-free.app`. Vos adresses de webhook
deviennent (l'identifiant de votre entreprise est affiche sur la page Profil) :

```
https://abcd-12-34-56.ngrok-free.app/api/webhooks/whatsapp/1
https://abcd-12-34-56.ngrok-free.app/api/webhooks/meta/1
https://abcd-12-34-56.ngrok-free.app/api/webhooks/email/1
```

L'URL change a chaque redemarrage de ngrok en version gratuite : pensez a la mettre a jour
dans Meta Developers.

---

## 1. WhatsApp Business API (Cloud API)

### 1.1 Creer l'application

1. Allez sur https://developers.facebook.com et connectez-vous.
2. **Mes applications → Creer une application → Entreprise**.
3. Nommez l'application (par exemple « OmniVente »), associez-la a votre Business Portfolio.
4. Dans le tableau de bord, ajoutez le produit **WhatsApp → Configurer**.

### 1.2 Recuperer le Phone Number ID

1. Ouvrez **WhatsApp → Configuration de l'API**.
2. Meta fournit un numero de test immediatement utilisable.
3. Sous le selecteur « Numero de telephone de l'expediteur », copiez le **Phone number ID**
   (suite de chiffres, a ne pas confondre avec le numero lui-meme).
4. Notez aussi le **WhatsApp Business Account ID**, utile pour les modeles de message.

Pour passer en production, ajoutez votre vrai numero via **Ajouter un numero de telephone**
puis verifiez-le par SMS ou appel. Un numero deja actif sur l'application WhatsApp classique
doit d'abord en etre supprime.

### 1.3 Creer un token permanent (System User Token)

Le token affiche par defaut expire au bout de 24 heures. Pour un token permanent :

1. Allez sur https://business.facebook.com/settings.
2. **Utilisateurs → Utilisateurs systeme → Ajouter**, nom « omnivente-bot », role **Administrateur**.
3. Cliquez **Ajouter des actifs** : selectionnez votre application et votre compte WhatsApp
   Business, avec le controle total.
4. Cliquez **Generer un nouveau token** :
   - Application : celle creee en 1.1
   - Expiration : **Jamais**
   - Autorisations : `whatsapp_business_messaging`, `whatsapp_business_management`
5. Copiez le token immediatement, il n'est plus affiche ensuite.

### 1.4 Declarer le webhook

1. Dans l'application, **WhatsApp → Configuration → Webhooks → Modifier**.
2. URL de rappel : `https://votre-tunnel/api/webhooks/whatsapp/1`
3. Token de verification : la valeur de `WHATSAPP_VERIFY_TOKEN` (par defaut `omnivente_verify_token`).
4. Cliquez **Verifier et enregistrer**. FastAPI repond au defi `hub.challenge` automatiquement.
5. Abonnez-vous au champ **messages** (bouton « Gerer »).

### 1.5 Variables a renseigner

```env
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_TOKEN=EAAG...votre_token_permanent
WHATSAPP_VERIFY_TOKEN=omnivente_verify_token
```

### 1.6 Tester

Envoyez un message WhatsApp au numero configure depuis un telephone autorise (en mode test,
ajoutez le numero dans **Destinataires de test**). Le message doit apparaitre dans la boite de
reception d'OmniVente et recevoir une reponse automatique.

Test direct de l'API sans passer par un telephone :

```bash
curl -X POST "https://graph.facebook.com/v21.0/VOTRE_PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messaging_product":"whatsapp","to":"22890000000","type":"text","text":{"body":"Test OmniVente"}}'
```

Rappel important : hors fenetre de 24 heures apres le dernier message du client, seuls les
**modeles approuves** peuvent etre envoyes.

---

## 2. Email professionnel (SMTP et IMAP)

### 2.1 Gmail / Google Workspace

1. Activez la validation en deux etapes : https://myaccount.google.com/security
2. Ouvrez https://myaccount.google.com/apppasswords
3. Choisissez **Autre (nom personnalise)** → « OmniVente » → **Generer**.
4. Copiez le mot de passe de 16 caracteres et retirez les espaces.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=contact@votre-entreprise.com
SMTP_PASSWORD=abcdefghijklmnop
```

Reception IMAP : `imap.gmail.com`, port 993, SSL, memes identifiants.

### 2.2 Outlook / Microsoft 365

1. Activez l'authentification multifacteur sur https://account.microsoft.com/security
2. **Options de securite avancees → Mots de passe d'application → Creer**.

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=contact@votre-entreprise.com
SMTP_PASSWORD=le_mot_de_passe_application
```

Reception IMAP : `outlook.office365.com`, port 993, SSL.

Sur Microsoft 365 professionnel, l'administrateur doit parfois autoriser
l'authentification SMTP : centre d'administration → Utilisateurs → Courrier → Gerer les
applications de messagerie → cocher **SMTP authentifie**.

### 2.3 Hebergeur mutualise (OVH, Hostinger, cPanel)

Les parametres se trouvent dans l'espace client, rubrique « Messagerie ». Modele courant :

```env
SMTP_HOST=ssl0.ovh.net
SMTP_PORT=587
SMTP_USER=contact@votre-domaine.com
SMTP_PASSWORD=votre_mot_de_passe
```

### 2.4 Tester l'envoi

```bash
cd backend
python -c "from app.services.channels import send_email; print(send_email('vous@mail.com','Test OmniVente','Ceci est un test.'))"
```

`True` signifie que le message est parti. `False` indique un identifiant refuse ou un port bloque.

### 2.5 Recevoir les emails dans OmniVente

Faites appeler le webhook email par votre relais (script IMAP, Zapier, Make, Mailgun Routes) :

```bash
curl -X POST "http://127.0.0.1:8000/api/webhooks/email/1" \
  -H "Content-Type: application/json" \
  -d '{"from":"client@mail.com","name":"Fatou Diallo","subject":"Demande de devis","body":"Bonjour, avez-vous des sacs en cuir ?"}'
```

---

## 3. Facebook Messenger

1. Dans la meme application Meta, ajoutez le produit **Messenger → Configurer**.
2. Section **Jetons d'acces** : cliquez **Ajouter ou supprimer des Pages**, selectionnez votre
   Page professionnelle, accordez les autorisations.
3. Cliquez **Generer un jeton** en face de la Page et copiez-le. Notez aussi l'**ID de la Page**
   (visible dans Parametres de la Page → A propos).
4. Section **Webhooks → Ajouter une URL de rappel** :
   - URL : `https://votre-tunnel/api/webhooks/meta/1`
   - Token de verification : valeur de `META_VERIFY_TOKEN`
5. Cliquez **Verifier et enregistrer**, puis **Ajouter des abonnements** sur la Page et cochez
   `messages` et `messaging_postbacks`.

```env
META_PAGE_TOKEN=EAAG...jeton_de_page
META_VERIFY_TOKEN=omnivente_verify_token
```

Renseignez l'ID de la Page dans OmniVente : page **Profil → Facebook / Instagram — Page ID**.

---

## 4. Instagram Direct

Prerequis : un compte Instagram **professionnel** ou **createur**, relie a la Page Facebook
configuree ci-dessus.

1. Instagram → Parametres → Compte → **Passer a un compte professionnel**.
2. Instagram → Parametres → **Comptes liés** → connectez la Page Facebook.
3. Dans l'application Meta, ajoutez le produit **Instagram → Configuration de l'API avec
   connexion Facebook**.
4. Dans **Webhooks**, choisissez l'objet **Instagram**, memes URL et token de verification
   qu'en section 3 ; abonnez-vous a `messages`.
5. Dans l'application Instagram : Parametres → Confidentialite → Messages → activez
   **Autoriser l'acces aux messages** pour les outils tiers.

Aucune variable supplementaire : `META_PAGE_TOKEN` couvre Messenger et Instagram. OmniVente
distingue les deux canaux grace au champ `object` du webhook (`page` ou `instagram`) et
applique le fond degrade rose/violet aux conversations Instagram.

---

## 5. Passage en production

| Etape | Action |
|---|---|
| Verification de l'entreprise | Meta Business Suite → Parametres → Informations sur l'entreprise → **Commencer la verification** |
| Autorisations avancees | Application → Verification de l'application → demander `whatsapp_business_messaging`, `pages_messaging`, `instagram_manage_messages` |
| Politique de confidentialite | URL publique obligatoire, a renseigner dans les parametres de base de l'application |
| Mode Live | Basculer l'interrupteur **Developpement → Live** en haut du tableau de bord |
| Webhook stable | Remplacer le tunnel ngrok par un domaine avec certificat TLS valide |
| Secrets | Regenerer `SECRET_KEY` et ne jamais versionner le fichier `.env` |

---

## 6. Diagnostic

| Symptome | Cause frequente | Correction |
|---|---|---|
| « The URL couldn't be validated » | Token de verification different | Alignez `WHATSAPP_VERIFY_TOKEN` / `META_VERIFY_TOKEN` avec la valeur saisie chez Meta |
| Webhook valide mais aucun message recu | Abonnement au champ `messages` manquant | Section Webhooks → Gerer → cochez `messages` |
| Erreur 401 a l'envoi | Token expire (token temporaire de 24 h) | Generez un System User Token permanent (section 1.3) |
| Erreur 131030 | Destinataire non autorise en mode test | Ajoutez le numero dans les destinataires de test |
| Erreur 131047 | Fenetre de 24 h depassee | Utilisez un modele de message approuve |
| SMTP `535 authentication failed` | Mot de passe de compte au lieu du mot de passe d'application | Regenerez un mot de passe d'application |
| SMTP silencieux | Port 587 bloque par le reseau | Essayez le port 465 en SSL ou un autre reseau |
| Messages Instagram absents | Acces aux messages desactive | Instagram → Confidentialite → Messages → autoriser l'acces |

Sans cle configuree, OmniVente reste pleinement utilisable : les reponses sont enregistrees en
base et journalisees dans la console, ce qui permet de tout tester avant de brancher les canaux.
