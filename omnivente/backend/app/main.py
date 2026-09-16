"""Point d'entree FastAPI d'OmniVente.

Au demarrage, l'application se connecte a la base PostgreSQL locale definie
dans `DATABASE_URL` et cree les tables manquantes.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, messages, orders, products, webhooks
from app.core.config import settings
from app.core.database import engine, init_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnivente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Connexion a PostgreSQL : %s", settings.DATABASE_URL.split("@")[-1])
    await init_models()
    logger.info("Tables verifiees / creees avec succes.")
    yield
    await engine.dispose()
    logger.info("Pool de connexions ferme.")


app = FastAPI(
    title="OmniVente API",
    description=(
        "Commerce conversationnel et billetterie omnicanale pour les PME. "
        "WhatsApp, Instagram, Messenger et Email dans une seule boite de reception."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
app.include_router(webhooks.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Sante"])
async def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "status": "en ligne",
        "docs": "/docs",
    }


@app.get("/health", tags=["Sante"])
async def health() -> dict:
    """Verifie que la connexion PostgreSQL repond."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"database": "connectee", "status": "ok"}
