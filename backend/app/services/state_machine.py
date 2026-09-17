"""Machine d'état du parcours de vente (aucune dépendance base de données).

    catalogue → quantite → mode → creneau → [position] → validation → fin

Chaque étape valide l'entrée du client, gère les ruptures de stock et renvoie
le message suivant ainsi que les réponses rapides à afficher sur le canal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

STEPS = ("catalogue", "quantite", "mode", "creneau", "position", "validation", "fin")


def fcfa(value: float) -> str:
    return f"{int(value):,}".replace(",", " ") + " FCFA"


@dataclass
class Reply:
    text: str
    step: str
    quick: list[str] = field(default_factory=list)
    order: dict | None = None      # renseigné à la validation : la commande à créer


def new_session() -> dict:
    return {"step": "catalogue", "product_ref": None, "quantity": 1,
            "fulfilment": None, "slot": None, "place": None}


def catalogue_text(catalog: list[dict]) -> str:
    lines = [
        f"{p['position']} - {p['name']} ({fcfa(p['price'])})" + ("" if p["in_stock"] else " — épuisé")
        for p in catalog
    ]
    return "Voici notre catalogue :\n" + "\n".join(lines) + "\n\nRépondez par le numéro de votre choix."


def greeting(name: str, shop: dict, catalog: list[dict]) -> Reply:
    first = (name or "").split(" ")[0] or "à vous"
    return Reply(
        text=f"Bonjour {first} 👋 Bienvenue chez {shop.get('company', 'notre boutique')}.\n\n"
             + catalogue_text(catalog),
        step="catalogue",
        quick=[str(p["position"]) for p in catalog[:5]],
    )


def _available(catalog: list[dict], limit: int = 3) -> str:
    """Liste courte des articles réellement disponibles, proposés en repli."""
    disponibles = [p for p in catalog if p["in_stock"] and p["quantity"] > 0][:limit]
    return "\n".join(f"{p['position']} - {p['name']} ({fcfa(p['price'])})" for p in disponibles)


def _find(catalog: list[dict], ref: str | None) -> dict | None:
    return next((p for p in catalog if p["ref"] == ref), None)


def _summary(session: dict, product: dict) -> str:
    total = product["price"] * session["quantity"]
    mode = "Livraison" if session["fulfilment"] == "livraison" else "Retrait en boutique"
    place_label = "Adresse" if session["fulfilment"] == "livraison" else "Point de retrait"
    return (
        "Récapitulatif de votre commande\n\n"
        f"• Article : {product['name']} ({product['ref']})\n"
        f"• Quantité : {session['quantity']}\n"
        f"• Total : {fcfa(total)}\n"
        f"• {mode} : {session['slot']}\n"
        f"• {place_label} : {session['place']}\n\n"
        "1 - Confirmer la commande\n2 - Modifier"
    )


def advance(session: dict, text: str, catalog: list[dict], shop: dict,
            choice: int | None = None) -> tuple[dict, Reply]:
    """Fait avancer la conversation d'une étape.

    `choice` est le numéro déjà extrait du message (par regex ou par Groq).
    Renvoie la session mise à jour et la réponse à envoyer au client.
    """
    step = session.get("step", "catalogue")
    text = (text or "").strip()

    # ---------------- Étape 1 : choix de l'article ----------------
    if step == "catalogue":
        if choice is None or not 1 <= choice <= len(catalog):
            return session, Reply(
                "Je n'ai pas reconnu ce numéro. Tapez un chiffre entre 1 et "
                f"{len(catalog)} pour choisir un article.",
                "catalogue", [str(p["position"]) for p in catalog[:5]])

        product = catalog[choice - 1]
        # ---------------- Étape 3 : vérification du stock ----------------
        if not product["in_stock"] or product["quantity"] <= 0:
            return session, Reply(
                f"Le {product['name']} est en rupture de stock pour le moment. 😔\n"
                f"Voici ce qui est disponible immédiatement :\n{_available(catalog)}\n\n"
                "Répondez par un numéro.",
                "catalogue", [str(p["position"]) for p in catalog if p["in_stock"]][:4])

        session.update(step="quantite", product_ref=product["ref"])
        return session, Reply(
            f"{product['name']} — {fcfa(product['price'])} l'unité.\n"
            "Combien d'exemplaires souhaitez-vous ? (Tapez un chiffre : 1, 2, 3…)",
            "quantite", ["1", "2", "3", "5"])

    product = _find(catalog, session.get("product_ref"))
    if product is None and step in ("quantite", "mode", "creneau", "position", "validation"):
        session = new_session()
        return session, Reply("Reprenons depuis le début.\n\n" + catalogue_text(catalog),
                              "catalogue", [str(p["position"]) for p in catalog[:5]])

    # ---------------- Étape 2 : quantité ----------------
    if step == "quantite":
        if choice is None or choice < 1:
            return session, Reply("Indiquez une quantité en chiffres, par exemple 2.",
                                  "quantite", ["1", "2", "3", "5"])
        if choice > product["quantity"]:
            return session, Reply(
                f"Il ne reste que {product['quantity']} unités de {product['name']}. "
                f"Indiquez une quantité inférieure ou égale à {product['quantity']}.",
                "quantite", ["1", "2", str(product["quantity"])])

        session.update(step="mode", quantity=min(choice, 99))
        total = product["price"] * session["quantity"]
        return session, Reply(
            f"{session['quantity']} × {product['name']} = {fcfa(total)}.\n\n"
            "Comment souhaitez-vous récupérer votre commande ?\n"
            "1 - Livraison à domicile\n2 - Retrait en boutique",
            "mode", ["1", "2"])

    # ---------------- Étape 4 : mode de retrait ----------------
    if step == "mode":
        if choice not in (1, 2):
            return session, Reply(
                "Tapez 1 pour la livraison à domicile, ou 2 pour le retrait en boutique.",
                "mode", ["1", "2"])
        session["fulfilment"] = "livraison" if choice == 1 else "retrait"
        session["step"] = "creneau"
        question = (
            "Quel jour et à quelle heure souhaitez-vous être livré ? (ex. : jeudi 18 septembre à 14h00)"
            if choice == 1 else
            f"Quel jour et à quelle heure passerez-vous à « {shop.get('pickup_point', 'la boutique')} » ? "
            "(ex. : jeudi 18 septembre à 10h30)")
        return session, Reply(question, "creneau", ["Jeudi 10h30", "Vendredi 15h00", "Samedi matin"])

    # ---------------- Étape 5 : créneau (et position si livraison) ----------------
    if step == "creneau":
        if len(text) < 3:
            return session, Reply(
                "Précisez le jour et l'heure, par exemple « jeudi 18 septembre à 10h30 ».",
                "creneau", ["Jeudi 10h30", "Vendredi 15h00"])
        session["slot"] = text
        if session["fulfilment"] == "livraison":
            session["step"] = "position"
            return session, Reply(
                "Merci. Envoyez maintenant votre position GPS (ou le nom de votre quartier) "
                "pour guider le livreur.",
                "position", ["📍 Partager ma position"])
        session["place"] = shop.get("pickup_point", "Boutique")
        session["step"] = "validation"
        return session, Reply(_summary(session, product), "validation", ["1", "2"])

    if step == "position":
        session["place"] = text
        session["step"] = "validation"
        return session, Reply(_summary(session, product), "validation", ["1", "2"])

    # ---------------- Étape 6 : validation et création de la commande ----------------
    if step == "validation":
        if choice == 1:
            total = product["price"] * session["quantity"]
            order = {
                "product_ref": product["ref"],
                "quantity": session["quantity"],
                "amount": total,
                "fulfilment": session["fulfilment"],
                "slot": session["slot"],
                "place": session["place"],
            }
            session["step"] = "fin"
            return session, Reply(
                "C'est enregistré ✅\nVotre commande est confirmée pour un montant de "
                f"{fcfa(total)}.\nNous vous écrivons dès qu'elle est prête.",
                "fin", ["Nouvelle commande"], order=order)
        if choice == 2:
            session = new_session()
            return session, Reply("Pas de souci, reprenons.\n\n" + catalogue_text(catalog),
                                  "catalogue", [str(p["position"]) for p in catalog[:5]])
        return session, Reply("Tapez 1 pour confirmer la commande, ou 2 pour la modifier.",
                              "validation", ["1", "2"])

    # ---------------- Après une commande : nouveau cycle ----------------
    session = new_session()
    return session, Reply(catalogue_text(catalog), "catalogue",
                          [str(p["position"]) for p in catalog[:5]])
