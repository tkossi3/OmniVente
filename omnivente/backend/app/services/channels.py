"""Envoi sortant vers les canaux externes.

Si les cles ne sont pas encore configurees (voir GUIDE_CONFIGURATION_CANAUX.md),
le message est simplement journalise et conserve en base : l'application reste
fonctionnelle de bout en bout en local.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings
from app.models.enums import Channel

logger = logging.getLogger("omnivente.channels")

GRAPH_API = "https://graph.facebook.com/v21.0"


async def send_whatsapp(to: str, body: str) -> bool:
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.info("[WhatsApp non configure] -> %s : %s", to, body)
        return False
    url = f"{GRAPH_API}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, headers=headers)
    if response.status_code >= 400:
        logger.error("Echec envoi WhatsApp (%s) : %s", response.status_code, response.text)
        return False
    return True


async def send_meta_message(recipient_id: str, body: str) -> bool:
    """Messenger et Instagram Direct utilisent le meme endpoint Graph."""
    if not settings.META_PAGE_TOKEN:
        logger.info("[Meta non configure] -> %s : %s", recipient_id, body)
        return False
    url = f"{GRAPH_API}/me/messages"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": body}}
    params = {"access_token": settings.META_PAGE_TOKEN}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, params=params)
    if response.status_code >= 400:
        logger.error("Echec envoi Meta (%s) : %s", response.status_code, response.text)
        return False
    return True


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info("[SMTP non configure] -> %s : %s", to, body)
        return False
    message = EmailMessage()
    message["From"] = settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as exc:  # pragma: no cover - dependant de l'environnement
        logger.error("Echec envoi email : %s", exc)
        return False


async def dispatch(channel: str, destination: str, body: str, subject: str = "OmniVente") -> bool:
    """Route le message sortant vers le bon canal."""
    if channel == Channel.WHATSAPP.value:
        return await send_whatsapp(destination, body)
    if channel in {Channel.MESSENGER.value, Channel.INSTAGRAM.value}:
        return await send_meta_message(destination, body)
    if channel == Channel.EMAIL.value:
        return send_email(destination, subject, body)
    logger.warning("Canal inconnu : %s", channel)
    return False
