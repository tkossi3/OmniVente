"""Schemas Pydantic pour l'inscription, la connexion et le profil entreprise."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Sector


class TenantRegister(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    sector: Sector
    description: str = Field(default="", max_length=4000)
    address: str = Field(default="", max_length=200)
    district: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    currency: str = Field(default="FCFA", max_length=10)
    password: str = Field(min_length=6, max_length=128)


class TenantLogin(BaseModel):
    email: EmailStr
    password: str


class TenantUpdate(BaseModel):
    company_name: Optional[str] = None
    sector: Optional[Sector] = None
    description: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    currency: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    meta_page_id: Optional[str] = None
    smtp_user: Optional[str] = None


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    sector: str
    description: str
    address: str
    district: str
    city: str
    email: EmailStr
    phone: str
    currency: str
    whatsapp_phone_number_id: str
    meta_page_id: str
    smtp_user: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant: TenantRead
