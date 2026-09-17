"""OmniVente — API du commerce conversationnel omnicanal."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import clients, conversations, orders, products, stats, tenants, webhooks
from app.services import groq_client, mail_poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s · %(levelname)s · %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        from scripts.seed import run as seed_run
        logger.info("AUTO_SEED activé : vérification des tables et du catalogue…")
        await asyncio.to_thread(seed_run, settings.auto_seed_demo)

    poll_task = asyncio.create_task(mail_poller.run_forever(settings.default_tenant))
    try:
        yield
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="OmniVente API",
    description="Vendez sur WhatsApp, Instagram, Messenger et e-mail depuis un seul tableau de bord.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins or ["*"],
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (tenants, products, orders, clients, conversations, stats, webhooks):
    app.include_router(module.router)
app.include_router(tenants.auth_router)


@app.get("/health", tags=["Service"])
def health():
    return {
        "status": "ok",
        "environment": settings.app_env,
        "agent": {"provider": "groq", "model": settings.groq_model,
                  "configured": groq_client.is_enabled()},
        "mail_poller": {"enabled": settings.mail_poll_enabled,
                        "configured": bool(settings.sales_email and settings.sales_email_app_password)},
        "whatsapp": {"configured": bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)},
        "meta": {"configured": bool(settings.meta_page_access_token)},
    }
