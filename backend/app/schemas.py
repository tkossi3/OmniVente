"""Schémas Pydantic : contrats d'entrée et de sortie de l'API."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Channel = Literal["whatsapp", "instagram", "messenger", "email"]
Status = Literal["preparer", "livraison", "retrait", "termine", "probleme"]


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref: str
    position: int
    name: str
    price: float
    quantity: int
    in_stock: bool
    category: str | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: Channel
    phone: str | None = None
    email: str | None = None
    location: str | None = None
    created_at: datetime
    last_seen_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    quantity: int
    amount: float
    channel: Channel
    status: Status
    fulfilment: Literal["livraison", "retrait"]
    slot: str | None = None
    place: str | None = None
    created_at: datetime
    client: ClientOut
    product: ProductOut


class OrderStatusIn(BaseModel):
    status: Status


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: Channel
    direction: Literal["in", "out"]
    body: str
    step: str | None = None
    created_at: datetime


class ChatIn(BaseModel):
    """Message entrant, qu'il vienne d'un webhook ou du simulateur du tableau de bord."""

    channel: Channel = "whatsapp"
    external_id: str = Field(..., description="Numéro WhatsApp, PSID Meta ou adresse e-mail")
    name: str = "Client"
    text: str


class ChatOut(BaseModel):
    reply: str
    step: str
    quick_replies: list[str] = []
    order_reference: str | None = None


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    company: str
    sector: str | None = None
    legal_form: str | None = None
    tax_id: str | None = None
    manager: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    currency: str
    pickup_point: str | None = None
    delivery_zone: str | None = None
    opening_hours: str | None = None
    about: str | None = None


class TenantIn(BaseModel):
    company: str | None = None
    sector: str | None = None
    legal_form: str | None = None
    tax_id: str | None = None
    manager: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    currency: str | None = None
    pickup_point: str | None = None
    delivery_zone: str | None = None
    opening_hours: str | None = None
    about: str | None = None


class StatsOut(BaseModel):
    revenue: float
    orders_total: int
    orders_by_status: dict[str, int]
    revenue_by_channel: dict[str, float]
    messages_by_channel: dict[str, list[int]]
    days: list[str]
