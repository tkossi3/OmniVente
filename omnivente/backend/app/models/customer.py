"""Client final d'une PME, identifie par son canal d'origine."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    external_ref: Mapped[str] = mapped_column(String(80), default="", index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="Client")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    channel: Mapped[str] = mapped_column(String(30), default="whatsapp")

    address: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    conversation_stage: Mapped[str] = mapped_column(String(40), default="accueil")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="customers")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="customer", cascade="all, delete-orphan")
