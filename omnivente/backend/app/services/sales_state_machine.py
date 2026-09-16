"""Machine a etats de vente conversationnelle.

Elle decide de l'etape suivante a partir de l'etape courante et de l'intention
detectee dans le message du client.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from app.models.enums import ConversationStage

# Intentions reconnues par le detecteur de l'agent IA.
INTENT_GREETING = "salutation"
INTENT_CATALOG = "catalogue"
INTENT_PRICE = "prix"
INTENT_AVAILABILITY = "disponibilite"
INTENT_ORDER = "commande"
INTENT_DELIVERY = "livraison"
INTENT_PAYMENT = "paiement"
INTENT_CONFIRM = "confirmation"
INTENT_CANCEL = "annulation"
INTENT_FAQ = "faq"
INTENT_OTHER = "autre"


@dataclass
class Transition:
    intent: str
    next_stage: str


@dataclass
class StageDefinition:
    stage: str
    goal: str
    transitions: List[Transition] = field(default_factory=list)


TRANSITIONS: Dict[str, Dict[str, str]] = {
    ConversationStage.ACCUEIL.value: {
        INTENT_GREETING: ConversationStage.DECOUVERTE.value,
        INTENT_CATALOG: ConversationStage.PROPOSITION.value,
        INTENT_PRICE: ConversationStage.PROPOSITION.value,
        INTENT_AVAILABILITY: ConversationStage.PROPOSITION.value,
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_FAQ: ConversationStage.DECOUVERTE.value,
        INTENT_OTHER: ConversationStage.DECOUVERTE.value,
    },
    ConversationStage.DECOUVERTE.value: {
        INTENT_CATALOG: ConversationStage.PROPOSITION.value,
        INTENT_PRICE: ConversationStage.PROPOSITION.value,
        INTENT_AVAILABILITY: ConversationStage.PROPOSITION.value,
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_CANCEL: ConversationStage.CLOTURE.value,
        INTENT_OTHER: ConversationStage.DECOUVERTE.value,
    },
    ConversationStage.PROPOSITION.value: {
        INTENT_PRICE: ConversationStage.NEGOCIATION.value,
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_CONFIRM: ConversationStage.COLLECTE_INFOS.value,
        INTENT_CANCEL: ConversationStage.CLOTURE.value,
        INTENT_OTHER: ConversationStage.PROPOSITION.value,
    },
    ConversationStage.NEGOCIATION.value: {
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_CONFIRM: ConversationStage.COLLECTE_INFOS.value,
        INTENT_CANCEL: ConversationStage.CLOTURE.value,
        INTENT_OTHER: ConversationStage.NEGOCIATION.value,
    },
    ConversationStage.COLLECTE_INFOS.value: {
        INTENT_DELIVERY: ConversationStage.CONFIRMATION.value,
        INTENT_PAYMENT: ConversationStage.CONFIRMATION.value,
        INTENT_CONFIRM: ConversationStage.CONFIRMATION.value,
        INTENT_CANCEL: ConversationStage.CLOTURE.value,
        INTENT_OTHER: ConversationStage.COLLECTE_INFOS.value,
    },
    ConversationStage.CONFIRMATION.value: {
        INTENT_CONFIRM: ConversationStage.CLOTURE.value,
        INTENT_CANCEL: ConversationStage.CLOTURE.value,
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_OTHER: ConversationStage.CONFIRMATION.value,
    },
    ConversationStage.CLOTURE.value: {
        INTENT_GREETING: ConversationStage.DECOUVERTE.value,
        INTENT_CATALOG: ConversationStage.PROPOSITION.value,
        INTENT_ORDER: ConversationStage.COLLECTE_INFOS.value,
        INTENT_OTHER: ConversationStage.CLOTURE.value,
    },
}

STAGE_GOALS: Dict[str, str] = {
    ConversationStage.ACCUEIL.value: "Souhaiter la bienvenue et identifier le besoin.",
    ConversationStage.DECOUVERTE.value: "Comprendre ce que le client recherche.",
    ConversationStage.PROPOSITION.value: "Proposer des produits precis avec leur prix.",
    ConversationStage.NEGOCIATION.value: "Lever les objections de prix et rassurer.",
    ConversationStage.COLLECTE_INFOS.value: "Recuperer nom, quantite, adresse et mode de retrait.",
    ConversationStage.CONFIRMATION.value: "Recapituler la commande et la faire valider.",
    ConversationStage.CLOTURE.value: "Confirmer la prise en charge et remercier.",
}


class SalesStateMachine:
    """Transitions deterministes entre les etapes de vente."""

    @staticmethod
    def next_stage(current_stage: str, intent: str) -> str:
        stage = current_stage if current_stage in TRANSITIONS else ConversationStage.ACCUEIL.value
        table = TRANSITIONS[stage]
        return table.get(intent, table.get(INTENT_OTHER, stage))

    @staticmethod
    def goal(stage: str) -> str:
        return STAGE_GOALS.get(stage, STAGE_GOALS[ConversationStage.ACCUEIL.value])

    @staticmethod
    def is_closing(stage: str) -> bool:
        return stage in {
            ConversationStage.CONFIRMATION.value,
            ConversationStage.CLOTURE.value,
        }
