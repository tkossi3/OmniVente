from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Channel, OrderStatus


class OrderItemCreate(BaseModel):
    product_id: Optional[int] = None
    product_name: str = ""
    quantity: int = Field(default=1, ge=1)
    unit_price: float = 0.0


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    customer_id: int
    channel: Channel = Channel.WHATSAPP
    status: OrderStatus = OrderStatus.A_PREPARER
    delivery_address: str = ""
    delivery_note: str = ""
    items: List[OrderItemCreate] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    delivery_address: Optional[str] = None
    delivery_note: Optional[str] = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    customer_id: int
    reference: str
    status: str
    channel: str
    total_amount: float
    currency: str
    delivery_address: str
    delivery_note: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead] = []
    customer_name: str = ""


class SwimlaneColumn(BaseModel):
    status: str
    label: str
    count: int
    orders: List[OrderRead]


class DashboardStats(BaseModel):
    orders_total: int
    orders_open: int
    revenue: float
    currency: str
    customers_total: int
    messages_unread: int
    by_channel: dict[str, int]
    by_status: dict[str, int]
