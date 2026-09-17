"""Webhooks des canaux. Meta vérifie l'URL en GET, puis livre les messages en POST."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_tenant_by_slug
from app.models import Tenant
from app.routers.conversations import process_incoming
from app.schemas import ChatIn
from app.services import channels

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


def _verify(request: Request, expected: str) -> PlainTextResponse:
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == expected:
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(403, "Jeton de vérification invalide.")


@router.get("/whatsapp/{slug}")
def verify_whatsapp(slug: str, request: Request,
                    tenant: Tenant = Depends(get_tenant_by_slug)):
    token = (tenant.integrations or {}).get("whatsapp", {}).get("verify_token")
    return _verify(request, token or settings.whatsapp_verify_token)


@router.post("/whatsapp/{slug}")
async def receive_whatsapp(slug: str, request: Request, db: Session = Depends(get_db),
                           tenant: Tenant = Depends(get_tenant_by_slug)):
    body = await request.json()
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            profiles = {c["wa_id"]: c.get("profile", {}).get("name", "Client")
                        for c in value.get("contacts", [])}
            for message in value.get("messages", []):
                sender = message.get("from")
                if message.get("type") == "location":
                    location = message["location"]
                    text = f"{location.get('latitude')}, {location.get('longitude')}"
                else:
                    text = message.get("text", {}).get("body", "")
                reply = process_incoming(db, tenant, ChatIn(
                    channel="whatsapp", external_id=sender,
                    name=profiles.get(sender, "Client"), text=text))
                channels.send_whatsapp(sender, reply.reply,
                                       (tenant.integrations or {}).get("whatsapp"))
    return {"status": "received"}


@router.get("/meta/{slug}")
def verify_meta(slug: str, request: Request,
                tenant: Tenant = Depends(get_tenant_by_slug)):
    token = (tenant.integrations or {}).get("meta", {}).get("verify_token")
    return _verify(request, token or settings.meta_verify_token)


@router.post("/meta/{slug}")
async def receive_meta(slug: str, request: Request, db: Session = Depends(get_db),
                       tenant: Tenant = Depends(get_tenant_by_slug)):
    body = await request.json()
    platform = "instagram" if body.get("object") == "instagram" else "messenger"
    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            text = event.get("message", {}).get("text")
            if not (sender and text):
                continue
            reply = process_incoming(db, tenant, ChatIn(
                channel=platform, external_id=sender, name="Client", text=text))
            channels.send_meta(sender, reply.reply, platform,
                               (tenant.integrations or {}).get("meta"))
    return {"status": "received"}


@router.post("/email/{slug}")
async def receive_email(slug: str, request: Request, db: Session = Depends(get_db),
                        tenant: Tenant = Depends(get_tenant_by_slug)):
    """Appelé par le relais IMAP (ou un service de réception type Mailgun)."""
    body = await request.json()
    sender = body.get("from")
    text = body.get("text", "")
    if not sender:
        raise HTTPException(422, "Expéditeur manquant.")
    reply = process_incoming(db, tenant, ChatIn(
        channel="email", external_id=sender, name=body.get("name", "Client"), text=text))
    channels.send_email(sender, reply.reply, config=(tenant.integrations or {}).get("email"))
    return {"status": "received"}
