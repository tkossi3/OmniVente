"""Dépendances partagées : résolution du commerçant (tenant) courant."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Tenant


def get_tenant(
    db: Session = Depends(get_db),
    x_tenant: str | None = Header(default=None, alias="X-Tenant"),
) -> Tenant:
    """Utilisé par le tableau de bord : le commerçant vient de l'en-tête X-Tenant."""
    slug = x_tenant or settings.default_tenant
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise HTTPException(404, f"Commerçant « {slug} » introuvable.")
    return tenant


def get_tenant_by_slug(slug: str, db: Session = Depends(get_db)) -> Tenant:
    """Utilisé par les webhooks : chaque canal appelle une URL propre au commerçant
    (ex. /webhooks/whatsapp/kino-steak), Meta n'envoie jamais d'en-tête X-Tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise HTTPException(404, f"Commerçant « {slug} » introuvable.")
    return tenant
