"""Profil de l'entreprise et configuration des canaux."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import Tenant
from app.schemas import TenantIn, TenantOut

router = APIRouter(prefix="/api/tenant", tags=["Entreprise"])


class IntegrationsIn(BaseModel):
    whatsapp: dict | None = None
    meta: dict | None = None
    email: dict | None = None


@router.get("", response_model=TenantOut)
def read_profile(tenant: Tenant = Depends(get_tenant)):
    return tenant


@router.put("", response_model=TenantOut)
def update_profile(payload: TenantIn, db: Session = Depends(get_db),
                   tenant: Tenant = Depends(get_tenant)):
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(tenant, key, value)
    db.commit()
    return tenant


@router.get("/integrations")
def read_integrations(tenant: Tenant = Depends(get_tenant)):
    """Les secrets ne sont jamais renvoyés en clair au tableau de bord."""
    data = dict(tenant.integrations or {})
    for block in data.values():
        if isinstance(block, dict):
            for key in list(block):
                if any(word in key for word in ("token", "secret", "password")):
                    block[key] = "••••••••"
    return data


@router.put("/integrations")
def update_integrations(payload: IntegrationsIn, db: Session = Depends(get_db),
                        tenant: Tenant = Depends(get_tenant)):
    current = dict(tenant.integrations or {})
    current.update(payload.model_dump(exclude_none=True))
    tenant.integrations = current
    db.commit()
    return {"status": "saved"}
