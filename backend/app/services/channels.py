"""Envoi des réponses vers WhatsApp, Messenger, Instagram et e-mail."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


def send_whatsapp(to: str, text: str, config: dict | None = None) -> bool:
    config = config or {}
    phone_number_id = config.get("phone_number_id") or settings.whatsapp_phone_number_id
    access_token = config.get("access_token") or settings.whatsapp_access_token
    if not (access_token and phone_number_id):
        logger.info("WhatsApp non configuré — message simulé vers %s", to)
        return False
    url = f"{GRAPH}/{phone_number_id}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text",
               "text": {"preview_url": False, "body": text}}
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=15) as http:
        response = http.post(url, json=payload, headers=headers)
    if response.status_code >= 400:
        logger.error("Envoi WhatsApp refusé : %s", response.text)
    return response.status_code < 400


def send_meta(psid: str, text: str, platform: str = "messenger", config: dict | None = None) -> bool:
    """Messenger et Instagram partagent le même point d'envoi de l'API Graph."""
    config = config or {}
    access_token = config.get("page_access_token") or settings.meta_page_access_token
    if not access_token:
        logger.info("Meta non configuré — message simulé vers %s (%s)", psid, platform)
        return False
    url = f"{GRAPH}/me/messages?access_token={access_token}"
    with httpx.Client(timeout=15) as http:
        response = http.post(url, json={"recipient": {"id": psid}, "message": {"text": text}})
    if response.status_code >= 400:
        logger.error("Envoi Meta refusé : %s", response.text)
    return response.status_code < 400


def send_email(to: str, text: str, subject: str = "Votre commande", config: dict | None = None) -> bool:
    config = config or {}
    sender = config.get("sales_email") or settings.sales_email
    password = config.get("app_password") or settings.sales_email_app_password
    if not (sender and password):
        logger.info("SMTP non configuré — e-mail simulé vers %s", to)
        return False
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)
    return True


def dispatch(channel: str, destination: str, text: str, config: dict | None = None,
             subject: str = "Votre commande") -> bool:
    if channel == "whatsapp":
        return send_whatsapp(destination, text, config)
    if channel in ("messenger", "instagram"):
        return send_meta(destination, text, channel, config)
    if channel == "email":
        return send_email(destination, text, subject=subject, config=config)
    return False
