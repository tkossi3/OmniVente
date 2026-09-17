"""Schéma relationnel : tenants, products, clients, orders, messages."""
from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CHANNELS = ("whatsapp", "instagram", "messenger", "email")
ORDER_STATUSES = ("preparer", "livraison", "retrait", "termine", "probleme")


class Tenant(Base):
    """Un commerçant abonné à OmniVente (architecture multi-tenant)."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str | None] = mapped_column(String(120))
    legal_form: Mapped[str | None] = mapped_column(String(40))
    tax_id: Mapped[str | None] = mapped_column(String(60))
    manager: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(240))
    city: Mapped[str | None] = mapped_column(String(80), default="Lomé")
    country: Mapped[str | None] = mapped_column(String(80), default="Togo")
    currency: Mapped[str] = mapped_column(String(10), default="FCFA")
    pickup_point: Mapped[str | None] = mapped_column(String(240))
    delivery_zone: Mapped[str | None] = mapped_column(String(240))
    opening_hours: Mapped[str | None] = mapped_column(String(160))
    about: Mapped[str | None] = mapped_column(Text)
    integrations: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    products: Mapped[list["Product"]] = relationship(back_populates="tenant")
    clients: Mapped[list["Client"]] = relationship(back_populates="tenant")
    orders: Mapped[list["Order"]] = relationship(back_populates="tenant")


class Product(Base):
    """Catalogue. `position` est le numéro que le client tape dans la conversation."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "ref", name="uq_product_ref"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    ref: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str | None] = mapped_column(String(80))

    tenant: Mapped[Tenant] = relationship(back_populates="products")


class Client(Base):
    """Contact identifié par son canal et son identifiant (numéro, PSID, e-mail)."""

    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", "external_id", name="uq_client_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), default="Client")
    channel: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    location: Mapped[str | None] = mapped_column(String(240))
    session_state: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="clients")
    orders: Mapped[list["Order"]] = relationship(back_populates="client")
    messages: Mapped[list["Message"]] = relationship(back_populates="client")


class Order(Base):
    """Commande créée automatiquement à la fin du parcours conversationnel."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    reference: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="preparer", index=True)
    fulfilment: Mapped[str] = mapped_column(String(20))       # livraison | retrait
    slot: Mapped[str | None] = mapped_column(String(120))     # jour et heure convenus
    place: Mapped[str | None] = mapped_column(String(240))    # adresse, GPS ou boutique
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="orders")
    client: Mapped[Client] = relationship(back_populates="orders")
    product: Mapped[Product] = relationship()


class Message(Base):
    """Historique complet des échanges, tous canaux confondus."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(10))        # in | out
    body: Mapped[str] = mapped_column(Text)
    step: Mapped[str | None] = mapped_column(String(30))      # étape de la machine d'état
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped[Client] = relationship(back_populates="messages")
