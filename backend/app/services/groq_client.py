"""Client Groq — compréhension du langage naturel de l'agent de vente.

La machine d'état garantit le parcours de commande ; Groq intervient pour
interpréter les réponses libres du client (« j'en veux deux » → 2) et pour
répondre aux questions hors parcours (horaires, adresse, moyens de paiement).
Si GROQ_API_KEY est absente, tout continue de fonctionner en mode déterministe.
"""
from __future__ import annotations

import json
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

try:  # le SDK reste optionnel au démarrage
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

_client = None


def get_client():
    global _client
    if _client is None and Groq and settings.groq_api_key:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def is_enabled() -> bool:
    return get_client() is not None


def _complete(system: str, user: str, max_tokens: int = 320, temperature: float = 0.2) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover - dépend du réseau
        logger.warning("Appel Groq impossible : %s", exc)
        return None


def extract_number(text: str, options: str, lo: int, hi: int) -> int | None:
    """Traduit une réponse libre en numéro de choix. Renvoie None si ambigu."""
    direct = re.search(r"\d+", text)
    if direct:
        value = int(direct.group())
        if lo <= value <= hi:
            return value

    words = {
        "un": 1, "une": 1, "premier": 1, "première": 1, "deux": 2, "deuxième": 2, "second": 2,
        "trois": 3, "troisième": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
        "neuf": 9, "dix": 10, "livraison": 1, "domicile": 1, "retrait": 2, "boutique": 2,
        "oui": 1, "confirme": 1, "confirmer": 1, "ok": 1, "non": 2, "annuler": 2, "modifier": 2,
    }
    for word, value in words.items():
        if re.search(rf"\b{word}\b", text.lower()) and lo <= value <= hi:
            return value

    raw = _complete(
        system=(
            "Tu convertis la réponse d'un client en un numéro de choix. "
            "Réponds uniquement par un objet JSON de la forme {\"choix\": <entier ou null>}. "
            "Aucun texte, aucun Markdown."
        ),
        user=f"Options proposées :\n{options}\n\nRéponse du client : « {text} »",
        max_tokens=40,
        temperature=0.0,
    )
    if not raw:
        return None
    try:
        value = json.loads(raw.replace("```json", "").replace("```", "").strip()).get("choix")
        return int(value) if value is not None and lo <= int(value) <= hi else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def answer_off_script(text: str, shop: dict, catalog: list[dict]) -> str | None:
    """Répond à une question qui sort du parcours de commande."""
    lines = "\n".join(
        f"{p['position']} - {p['name']} ({int(p['price']):,} FCFA)".replace(",", " ")
        + ("" if p["in_stock"] else " — épuisé")
        for p in catalog
    )
    return _complete(
        system=(
            "Tu es l'assistant de vente de la boutique décrite ci-dessous. "
            "Tu réponds en français, en deux phrases maximum, sur un ton chaleureux et direct. "
            "Tu ne promets rien qui ne figure pas dans les informations fournies. "
            "Tu termines toujours en invitant le client à taper le numéro de l'article souhaité."
        ),
        user=(
            f"Boutique : {shop.get('company')}\n"
            f"Adresse : {shop.get('address')}, {shop.get('city')}\n"
            f"Horaires : {shop.get('opening_hours')}\n"
            f"Point de retrait : {shop.get('pickup_point')}\n"
            f"Zone de livraison : {shop.get('delivery_zone')}\n"
            f"À propos : {shop.get('about')}\n\n"
            f"Catalogue :\n{lines}\n\n"
            f"Question du client : « {text} »"
        ),
        max_tokens=180,
        temperature=0.4,
    )
