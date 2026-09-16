from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import Channel, Direction


class MessageCreate(BaseModel):
    customer_id: int
    body: str
    channel: Optional[Channel] = None
    direction: Direction = Direction.OUTBOUND
    is_bot: bool = False


class IncomingMessage(BaseModel):
    """Message entrant simule ou recu via webhook."""

    channel: Channel = Channel.WHATSAPP
    external_ref: str
    full_name: str = "Client"
    body: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    customer_id: int
    channel: str
    direction: str
    body: str
    is_bot: bool
    is_read: bool
    created_at: datetime


class ConversationRead(BaseModel):
    customer_id: int
    full_name: str
    channel: str
    external_ref: str
    stage: str
    last_message: str
    last_message_at: Optional[datetime] = None
    unread: int


class ConversationDetail(BaseModel):
    customer_id: int
    full_name: str
    channel: str
    stage: str
    messages: List[MessageRead]


class BotReply(BaseModel):
    reply: str
    stage: str
    intent: str
    order_created: Optional[int] = None


class FaqRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    tags: str


class FaqCreate(BaseModel):
    question: str
    answer: str
    tags: str = ""
