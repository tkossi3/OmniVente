"""Entreprise (tenant) : chaque PME inscrite possede ses propres donnees."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    sector: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    address: Mapped[str] = mapped_column(String(200), default="")
    district: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(120), default="")

    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(40), default="")
    currency: Mapped[str] = mapped_column(String(10), default="FCFA")

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Parametres de canaux (remplis depuis l'ecran Profil)
    whatsapp_phone_number_id: Mapped[str] = mapped_column(String(80), default="")
    meta_page_id: Mapped[str] = mapped_column(String(80), default="")
    smtp_user: Mapped[str] = mapped_column(String(160), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="tenant", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="tenant", cascade="all, delete-orphan")
    faqs = relationship("FaqEntry", back_populates="tenant", cascade="all, delete-orphan")
