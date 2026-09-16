"""Messages omnicanaux (WhatsApp, Instagram, Messenger, Email)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)

    channel: Mapped[str] = mapped_column(String(30), default="whatsapp", index=True)
    direction: Mapped[str] = mapped_column(String(20), default="inbound")
    body: Mapped[str] = mapped_column(Text, default="")
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    external_id: Mapped[str] = mapped_column(String(120), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    tenant = relationship("Tenant", back_populates="messages")
    customer = relationship("Customer", back_populates="messages")
