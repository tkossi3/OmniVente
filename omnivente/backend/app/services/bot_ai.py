"""Agent de vente conversationnel.

Le moteur combine trois briques :
1. un detecteur d'intention lexical (francais, tolerant aux accents) ;
2. la machine a etats de vente (`SalesStateMachine`) ;
3. le RAG FAQ construit sur les reponses existantes du tenant.

Toutes les donnees proviennent de la base PostgreSQL locale : catalogue
produits, historique de conversation, reponses existantes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.models.customer import Customer
from app.models.enums import ConversationStage
from app.models.product import Product
from app.models.tenant import Tenant
from app.services.rag_faq import FaqDocument, FaqIndex, normalize, tokenize
from app.services.sales_state_machine import (
    INTENT_AVAILABILITY,
    INTENT_CANCEL,
    INTENT_CATALOG,
    INTENT_CONFIRM,
    INTENT_DELIVERY,
    INTENT_FAQ,
    INTENT_GREETING,
    INTENT_ORDER,
    INTENT_OTHER,
    INTENT_PAYMENT,
    INTENT_PRICE,
    SalesStateMachine,
)

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    INTENT_GREETING: ("bonjour", "bonsoir", "salut", "coucou", "hello", "bjr", "slt"),
    INTENT_CATALOG: ("catalogue", "produits", "articles", "disponible", "vous avez", "liste", "modeles"),
    INTENT_PRICE: ("prix", "combien", "cout", "tarif", "cher", "reduction", "remise", "promo"),
    INTENT_AVAILABILITY: ("stock", "dispo", "disponibilite", "reste", "encore"),
    INTENT_ORDER: ("commander", "commande", "acheter", "je prends", "je veux", "reserver", "achat"),
    INTENT_DELIVERY: ("livraison", "livrer", "adresse", "domicile", "retrait", "boutique", "quartier"),
    INTENT_PAYMENT: ("payer", "paiement", "mobile money", "flooz", "tmoney", "especes", "carte", "virement"),
    INTENT_CONFIRM: ("ok", "oui", "d accord", "daccord", "confirme", "valide", "parfait", "ca marche"),
    INTENT_CANCEL: ("annule", "annuler", "non merci", "laisse tomber", "plus tard", "stop"),
}

QUANTITY_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:x|pieces?|unites?|articles?)?\b")


@dataclass
class BotDecision:
    reply: str
    stage: str
    intent: str
    matched_products: List[Product]
    quantity: int
    should_create_order: bool


def detect_intent(text: str) -> str:
    haystack = normalize(text)
    scores: dict[str, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in haystack)
        if hits:
            scores[intent] = hits
    if not scores:
        return INTENT_OTHER
    # Une intention d'achat prime toujours sur une simple salutation.
    for priority in (INTENT_ORDER, INTENT_CANCEL, INTENT_CONFIRM, INTENT_DELIVERY, INTENT_PAYMENT):
        if priority in scores:
            return priority
    return max(scores.items(), key=lambda item: item[1])[0]


def extract_quantity(text: str) -> int:
    match = QUANTITY_PATTERN.search(normalize(text))
    if not match:
        return 1
    quantity = int(match.group(1))
    return quantity if 1 <= quantity <= 500 else 1


def match_products(text: str, products: Sequence[Product], limit: int = 3) -> List[Product]:
    tokens = set(tokenize(text))
    if not tokens:
        return []
    scored: list[tuple[int, Product]] = []
    for product in products:
        haystack = set(tokenize(f"{product.name} {product.category} {product.description} {product.sku}"))
        overlap = len(tokens & haystack)
        if overlap:
            scored.append((overlap, product))
    scored.sort(key=lambda item: (item[0], item[1].stock), reverse=True)
    return [product for _, product in scored[:limit]]


def format_price(amount: float, currency: str) -> str:
    return f"{amount:,.0f}".replace(",", " ") + f" {currency}"


class SalesBot:
    """Genere la reponse du vendeur virtuel pour un message entrant."""

    def __init__(
        self,
        tenant: Tenant,
        products: Sequence[Product],
        faq_documents: Sequence[FaqDocument],
    ) -> None:
        self.tenant = tenant
        self.products = list(products)
        self.faq_index = FaqIndex(faq_documents)

    # ------------------------------------------------------------------
    def handle(self, customer: Customer, body: str) -> BotDecision:
        intent = detect_intent(body)
        matched = match_products(body, self.products)
        quantity = extract_quantity(body)

        if intent == INTENT_OTHER and matched:
            intent = INTENT_CATALOG

        faq_match = self.faq_index.best_answer(body)
        if intent in {INTENT_OTHER, INTENT_GREETING} and faq_match and not matched:
            intent = INTENT_FAQ

        next_stage = SalesStateMachine.next_stage(customer.conversation_stage, intent)

        should_create_order = (
            intent in {INTENT_ORDER, INTENT_CONFIRM}
            and bool(matched)
        ) or (
            intent == INTENT_CONFIRM
            and customer.conversation_stage
            in {ConversationStage.CONFIRMATION.value, ConversationStage.COLLECTE_INFOS.value}
            and bool(matched)
        )

        reply = self._compose_reply(
            customer=customer,
            intent=intent,
            stage=next_stage,
            matched=matched,
            quantity=quantity,
            faq_answer=faq_match.document.answer if faq_match else None,
        )

        return BotDecision(
            reply=reply,
            stage=next_stage,
            intent=intent,
            matched_products=matched,
            quantity=quantity,
            should_create_order=should_create_order,
        )

    # ------------------------------------------------------------------
    def _catalog_teaser(self, limit: int = 3) -> str:
        available = [p for p in self.products if p.is_active][:limit]
        if not available:
            return "Notre catalogue est en cours de mise a jour."
        lines = [
            f"- {p.name} : {format_price(p.price, p.currency or self.tenant.currency)}"
            for p in available
        ]
        return "\n".join(lines)

    def _compose_reply(
        self,
        customer: Customer,
        intent: str,
        stage: str,
        matched: Sequence[Product],
        quantity: int,
        faq_answer: Optional[str],
    ) -> str:
        company = self.tenant.company_name
        currency = self.tenant.currency or "FCFA"
        name = customer.full_name or "cher client"

        if intent == INTENT_CANCEL:
            return (
                f"C'est note, {name}. Je garde votre demande de cote. "
                f"Ecrivez-nous des que vous etes pret, {company} reste disponible."
            )

        if intent == INTENT_FAQ and faq_answer:
            return faq_answer

        if intent == INTENT_GREETING:
            return (
                f"Bonjour {name}, bienvenue chez {company}. "
                "Dites-moi ce que vous cherchez, je vous oriente tout de suite.\n\n"
                f"Nos articles du moment :\n{self._catalog_teaser()}"
            )

        if intent in {INTENT_CATALOG, INTENT_AVAILABILITY}:
            if matched:
                lines = []
                for product in matched:
                    stock_note = (
                        f"en stock ({product.stock})" if product.stock > 0 else "sur commande"
                    )
                    lines.append(
                        f"- {product.name} : "
                        f"{format_price(product.price, product.currency or currency)} — {stock_note}"
                    )
                return (
                    "Voici ce que nous avons qui correspond :\n"
                    + "\n".join(lines)
                    + "\n\nSouhaitez-vous que je prepare une commande ?"
                )
            return (
                "Voici une selection de notre catalogue :\n"
                + self._catalog_teaser(limit=5)
                + "\n\nQuel article vous interesse ?"
            )

        if intent == INTENT_PRICE:
            if matched:
                product = matched[0]
                total = product.price * quantity
                return (
                    f"{product.name} est a "
                    f"{format_price(product.price, product.currency or currency)} l'unite. "
                    f"Pour {quantity} piece(s), le total est de {format_price(total, currency)}. "
                    "Je vous prepare la commande ?"
                )
            if faq_answer:
                return faq_answer
            return (
                "Nos prix dependent de l'article. Precisez-moi le produit exact "
                "et je vous donne le montant immediatement."
            )

        if intent == INTENT_ORDER:
            if matched:
                product = matched[0]
                total = product.price * quantity
                return (
                    f"Parfait. Je note {quantity} x {product.name} pour "
                    f"{format_price(total, currency)}.\n"
                    "Pour finaliser, indiquez-moi votre nom complet, votre quartier "
                    "et si vous preferez la livraison ou le retrait en boutique."
                )
            return (
                "Avec plaisir. Quel article souhaitez-vous commander, et en quelle quantite ?"
            )

        if intent == INTENT_DELIVERY:
            return (
                f"Nous livrons a {self.tenant.city or 'votre ville'} et le retrait est possible "
                f"a notre boutique ({self.tenant.address or 'adresse communiquee par message'}). "
                "Donnez-moi votre quartier et je vous confirme le delai."
            )

        if intent == INTENT_PAYMENT:
            return (
                "Vous pouvez payer par Mobile Money, en especes a la livraison ou "
                "par virement. Quel moyen vous arrange ?"
            )

        if intent == INTENT_CONFIRM:
            if matched:
                product = matched[0]
                total = product.price * quantity
                return (
                    f"Commande enregistree : {quantity} x {product.name}, "
                    f"{format_price(total, currency)}. "
                    "Notre equipe la prepare et revient vers vous avec le delai exact. Merci !"
                )
            return (
                "C'est note. Precisez-moi l'article et la quantite pour que je valide la commande."
            )

        if faq_answer:
            return faq_answer

        return (
            f"Merci pour votre message, {name}. "
            f"{SalesStateMachine.goal(stage)} "
            "Dites-moi l'article qui vous interesse et je m'occupe du reste."
        )
