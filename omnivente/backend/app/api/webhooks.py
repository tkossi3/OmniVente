"""Webhooks entrants Meta (WhatsApp, Messenger, Instagram) et email.

Le tenant est identifie par son id passe dans l'URL du webhook, ce qui permet
d'heberger plusieurs PME sur la meme instance :
    https://<votre-tunnel>/api/webhooks/whatsapp/3
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages import process_incoming
from app.core.config import settings
from app.core.database import get_db
from app.models.enums import Channel
from app.models.tenant import Tenant

logger = logging.getLogger("omnivente.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _get_tenant(db: AsyncSession, tenant_id: int) -> Tenant:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Entreprise introuvable.")
    return tenant


def _verify(request: Request, expected_token: str) -> Response:
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == expected_token:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Jeton de verification invalide.")


@router.get("/whatsapp/{tenant_id}")
async def verify_whatsapp(tenant_id: int, request: Request) -> Response:
    return _verify(request, settings.WHATSAPP_VERIFY_TOKEN)


@router.post("/whatsapp/{tenant_id}")
async def receive_whatsapp(
    tenant_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    tenant = await _get_tenant(db, tenant_id)
    payload = await request.json()
    handled = 0

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "Client")
                        for c in value.get("contacts", [])}
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = message.get("from", "")
                body = message.get("text", {}).get("body", "")
                if not sender or not body:
                    continue
                await process_incoming(
                    db=db,
                    tenant=tenant,
                    channel=Channel.WHATSAPP.value,
                    external_ref=sender,
                    body=body,
                    full_name=contacts.get(sender, "Client"),
                )
                handled += 1

    return {"status": "ok", "handled": handled}


@router.get("/meta/{tenant_id}")
async def verify_meta(tenant_id: int, request: Request) -> Response:
    return _verify(request, settings.META_VERIFY_TOKEN)


@router.post("/meta/{tenant_id}")
async def receive_meta(
    tenant_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Gere `page` (Messenger) et `instagram` (Direct)."""
    tenant = await _get_tenant(db, tenant_id)
    payload = await request.json()
    object_type = payload.get("object", "page")
    channel = (
        Channel.INSTAGRAM.value if object_type == "instagram" else Channel.MESSENGER.value
    )
    handled = 0

    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id", "")
            body = event.get("message", {}).get("text", "")
            if not sender or not body:
                continue
            await process_incoming(
                db=db,
                tenant=tenant,
                channel=channel,
                external_ref=sender,
                body=body,
                full_name="Client",
            )
            handled += 1

    return {"status": "ok", "channel": channel, "handled": handled}


@router.post("/email/{tenant_id}")
async def receive_email(
    tenant_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Point d'entree pour un relais IMAP ou un service d'email entrant.

    Corps attendu : {"from": "client@mail.com", "name": "...", "subject": "...", "body": "..."}
    """
    tenant = await _get_tenant(db, tenant_id)
    payload = await request.json()
    sender = payload.get("from", "")
    body = payload.get("body", "")
    if not sender or not body:
        raise HTTPException(status_code=422, detail="Champs 'from' et 'body' requis.")

    result = await process_incoming(
        db=db,
        tenant=tenant,
        channel=Channel.EMAIL.value,
        external_ref=sender,
        body=f"{payload.get('subject', '')}\n{body}".strip(),
        full_name=payload.get("name", "Client"),
    )
    return {"status": "ok", "reply": result.reply}
