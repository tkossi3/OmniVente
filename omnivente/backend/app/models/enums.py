"""Enumerations metier partagees par les modeles, schemas et services."""
from enum import Enum


class Sector(str, Enum):
    MARCHANDISES = "Vente de marchandises"
    HABILLEMENT = "Habillement"
    ELECTRONIQUE = "Electronique"
    RESTAURATION = "Restauration"
    SERVICES = "Services"


class Channel(str, Enum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    MESSENGER = "messenger"
    EMAIL = "email"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class OrderStatus(str, Enum):
    A_PREPARER = "a_preparer"
    EN_LIVRAISON = "en_livraison"
    RETRAIT_BOUTIQUE = "retrait_boutique"
    TERMINE = "termine"
    ANNULE = "annule"


class ConversationStage(str, Enum):
    """Etats de la machine a etats de vente."""

    ACCUEIL = "accueil"
    DECOUVERTE = "decouverte"
    PROPOSITION = "proposition"
    NEGOCIATION = "negociation"
    COLLECTE_INFOS = "collecte_infos"
    CONFIRMATION = "confirmation"
    CLOTURE = "cloture"


ORDER_STATUS_LABELS: dict[str, str] = {
    OrderStatus.A_PREPARER.value: "A preparer",
    OrderStatus.EN_LIVRAISON.value: "En cours de livraison",
    OrderStatus.RETRAIT_BOUTIQUE.value: "Retrait en boutique",
    OrderStatus.TERMINE.value: "Termine",
    OrderStatus.ANNULE.value: "Annule / Probleme",
}
