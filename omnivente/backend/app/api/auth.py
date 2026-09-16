"""Inscription d'une entreprise, connexion et profil."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.schemas.tenant import (
    TenantLogin,
    TenantRead,
    TenantRegister,
    TenantUpdate,
    Token,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: TenantRegister, db: AsyncSession = Depends(get_db)) -> Token:
    existing = await db.execute(select(Tenant).where(Tenant.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe deja avec cet email professionnel.",
        )

    tenant = Tenant(
        company_name=payload.company_name,
        sector=payload.sector.value,
        description=payload.description,
        address=payload.address,
        district=payload.district,
        city=payload.city,
        email=payload.email,
        phone=payload.phone,
        currency=payload.currency or "FCFA",
        hashed_password=hash_password(payload.password),
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)

    token = create_access_token(subject=tenant.id, extra={"email": tenant.email})
    return Token(access_token=token, tenant=TenantRead.model_validate(tenant))


@router.post("/login", response_model=Token)
async def login(payload: TenantLogin, db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(Tenant).where(Tenant.email == payload.email))
    tenant = result.scalar_one_or_none()
    if tenant is None or not verify_password(payload.password, tenant.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )
    token = create_access_token(subject=tenant.id, extra={"email": tenant.email})
    return Token(access_token=token, tenant=TenantRead.model_validate(tenant))


@router.get("/me", response_model=TenantRead)
async def me(tenant: Tenant = Depends(get_current_tenant)) -> TenantRead:
    return TenantRead.model_validate(tenant)


@router.patch("/me", response_model=TenantRead)
async def update_profile(
    payload: TenantUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    data = payload.model_dump(exclude_unset=True)
    if "sector" in data and data["sector"] is not None:
        data["sector"] = data["sector"].value if hasattr(data["sector"], "value") else data["sector"]
    for field, value in data.items():
        if value is not None:
            setattr(tenant, field, value)
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return TenantRead.model_validate(tenant)
