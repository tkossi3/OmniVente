"""Connexion asynchrone a la base PostgreSQL locale (SQLAlchemy 2.0 + asyncpg).

Aucune base en memoire n'est utilisee : le pool pointe directement sur
l'instance PostgreSQL declaree dans DATABASE_URL.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Classe de base pour tous les modeles SQLAlchemy."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependance FastAPI : fournit une session et la ferme proprement."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_models() -> None:
    """Cree toutes les tables dans PostgreSQL si elles n'existent pas."""
    # Import necessaire pour que Base.metadata connaisse tous les modeles.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
