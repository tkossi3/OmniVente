"""Authentification, profil de l'entreprise et configuration des canaux."""
import base64
import hashlib
import hmac
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import Tenant
from app.schemas import TenantIn, TenantOut

router = APIRouter(prefix="/api/tenant", tags=["Entreprise"])
auth_router = APIRouter(prefix="/api/auth", tags=["Authentification"])


class IntegrationsIn(BaseModel):
    whatsapp: dict | None = None
    meta: dict | None = None
    email: dict | None = None


class AuthCredentials(BaseModel):
    email: str
    password: str


class RegisterIn(AuthCredentials):
    company: str
    manager: str


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _password_matches(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _auth_data(tenant: Tenant) -> dict:
    return dict((tenant.integrations or {}).get("_auth") or {})


def _auth_response(tenant: Tenant) -> dict:
    return {
        "authenticated": True,
        "tenant": tenant.slug,
        "profile": {
            "company": tenant.company,
            "manager": tenant.manager,
            "email": tenant.email,
        },
    }


@auth_router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    password = payload.password
    company = payload.company.strip()
    manager = payload.manager.strip()
    if len(password) < 8:
        raise HTTPException(422, "Le mot de passe doit contenir au moins 8 caractères.")
    if not company or not manager:
        raise HTTPException(422, "Le nom de l'entreprise et le nom du responsable sont obligatoires.")
    existing = db.scalar(select(Tenant).where(Tenant.email.ilike(email)))
    if existing:
        if _auth_data(existing).get("password_hash"):
            raise HTTPException(409, "Cette adresse e-mail est déjà utilisée.")
        # Permet d'activer l'accès d'un commerçant créé par le script de
        # démonstration sans modifier son catalogue ni ses historiques.
        existing.integrations = {
            **dict(existing.integrations or {}),
            "_auth": {"password_hash": _password_hash(password)},
        }
        db.commit()
        return _auth_response(existing)

    base_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")[:60] or "entreprise"
    slug = base_slug
    suffix = 2
    while db.scalar(select(Tenant).where(Tenant.slug == slug)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    tenant = Tenant(slug=slug, company=company, manager=manager, email=email,
                    integrations={"_auth": {"password_hash": _password_hash(password)}})
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return _auth_response(tenant)


@auth_router.post("/login")
def login(payload: AuthCredentials, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    tenant = db.scalar(select(Tenant).where(Tenant.email.ilike(email)))
    if tenant is None or not _password_matches(payload.password, _auth_data(tenant).get("password_hash")):
        raise HTTPException(401, "Adresse e-mail ou mot de passe incorrect.")
    return _auth_response(tenant)


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
                if any(word in key.lower() for word in ("token", "secret", "password")):
                    block[key] = "••••••••"
    return data


@router.put("/integrations")
def update_integrations(payload: IntegrationsIn, db: Session = Depends(get_db),
                        tenant: Tenant = Depends(get_tenant)):
    current = dict(tenant.integrations or {})
    for channel, block in payload.model_dump(exclude_none=True).items():
        if block is None:
            continue
        saved = dict(current.get(channel) or {})
        for key, value in block.items():
            if value not in (None, "", "••••••••"):
                saved[key] = value
        current[channel] = saved
    tenant.integrations = current
    db.commit()
    return {"status": "saved"}
