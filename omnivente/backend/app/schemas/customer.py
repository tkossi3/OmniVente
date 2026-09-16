from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Channel


class CustomerCreate(BaseModel):
    full_name: str = Field(default="Client", max_length=160)
    phone: str = ""
    email: str = ""
    channel: Channel = Channel.WHATSAPP
    external_ref: str = ""
    address: str = ""
    city: str = ""
    notes: str = ""


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    full_name: str
    phone: str
    email: str
    channel: str
    external_ref: str
    address: str
    city: str
    notes: str
    conversation_stage: str
    created_at: datetime
