from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    sku: str = Field(default="", max_length=60)
    category: str = Field(default="", max_length=120)
    description: str = ""
    price: float = 0.0
    currency: str = "FCFA"
    stock: int = 0
    image_url: str = ""
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    created_at: datetime
