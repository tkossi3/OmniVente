"""Sondage IMAP — fait entrer les e-mails reçus dans le même moteur conversationnel.

Gmail (comme la plupart des messageries) n'offre pas de webhook gratuit pour les
messages entrants : contrairement à WhatsApp et Meta, il n'y a personne pour nous
notifier en temps réel. On interroge donc la boîte SALES_EMAIL toutes les
MAIL_POLL_SECONDS secondes, on traite les messages non lus avec la même machine
d'état que les autres canaux, puis on répond par SMTP.

Cette tâche tourne en arrière-plan pendant toute la vie du processus FastAPI
(démarrée dans app/main.py). Elle est volontairement synchrone en interne — imaplib
et smtplib n'ont pas d'API asynchrone — et s'exécute dans un thread à part
(asyncio.to_thread) pour ne jamais bloquer le serveur web.
"""
from __future__ import annotations

import asyncio
import email
import imaplib
import logging
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Tenant
from app.schemas import ChatIn
from app.services import channels

logger = logging.getLogger(__name__)


def _decode(value: str | None) -> str:
    if not value:
        return ""
    return "".join(
        part.decode(enc or "utf-8", errors="ignore") if isinstance(part, bytes) else part
        for part, enc in decode_header(value)
    )


def _body_text(message: Message) -> str:
    """Extrait le texte brut, en ignorant les pièces jointes et le HTML."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                return payload.decode(charset, errors="ignore").strip() if payload else ""
        return ""
    charset = message.get_content_charset() or "utf-8"
    payload = message.get_payload(decode=True)
    return payload.decode(charset, errors="ignore").strip() if payload else ""


def _poll_once(tenant_slug: str) -> int:
    """Une passe de sondage. Renvoie le nombre de messages traités."""
    if not (settings.sales_email and settings.sales_email_app_password):
        return 0

    # Import tardif : évite un cycle d'imports avec app.routers.conversations au démarrage.
    from app.routers.conversations import process_incoming

    processed = 0
    box = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        box.login(settings.sales_email, settings.sales_email_app_password)
        box.select("INBOX")
        status, data = box.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return 0
        message_ids = data[0].split()

        with SessionLocal() as db:
            tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
            if tenant is None:
                logger.warning("Sondage e-mail : commerçant « %s » introuvable.", tenant_slug)
                return 0

            for message_id in message_ids:
                status, raw = box.fetch(message_id, "(RFC822)")
                if status != "OK" or not raw or not raw[0]:
                    continue
                parsed = email.message_from_bytes(raw[0][1])
                sender_name, sender_addr = parseaddr(_decode(parsed.get("From")))
                text = _body_text(parsed)
                if not (sender_addr and text.strip()):
                    continue

                reply = process_incoming(db, tenant, ChatIn(
                    channel="email", external_id=sender_addr,
                    name=sender_name or sender_addr, text=text))
                channels.send_email(sender_addr, reply.reply,
                                    subject=f"Re : votre commande — {tenant.company}")
                processed += 1
        return processed
    finally:
        try:
            box.close()
        except Exception:  # boîte jamais ouverte, ou déjà fermée
            pass
        box.logout()


async def run_forever(tenant_slug: str) -> None:
    """Boucle de fond : sonde la boîte toutes les MAIL_POLL_SECONDS secondes."""
    if not settings.mail_poll_enabled:
        logger.info("Sondage e-mail désactivé (MAIL_POLL_ENABLED=false).")
        return
    if not (settings.sales_email and settings.sales_email_app_password):
        logger.info("Sondage e-mail inactif : SALES_EMAIL / SALES_EMAIL_APP_PASSWORD absents.")
        return

    logger.info("Sondage e-mail démarré (toutes les %ss).", settings.mail_poll_seconds)
    while True:
        try:
            count = await asyncio.to_thread(_poll_once, tenant_slug)
            if count:
                logger.info("Sondage e-mail : %s message(s) traité(s).", count)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # réseau, identifiants temporairement invalides, etc.
            logger.warning("Sondage e-mail interrompu : %s", exc)
        await asyncio.sleep(settings.mail_poll_seconds)
