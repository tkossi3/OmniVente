"""Dependances communes : recuperation du tenant authentifie via JWT."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.tenant import Tenant

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Connectez-vous pour acceder a cette ressource.",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expiree. Reconnectez-vous.",
        )
    result = await db.execute(select(Tenant).where(Tenant.id == int(payload["sub"])))
    tenant = result.scalar_one_or_none()
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte entreprise introuvable.",
        )
    return tenant
