"""Envoi des réponses vers WhatsApp, Messenger, Instagram et e-mail."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


def send_whatsapp(to: str, text: str) -> bool:
    if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
        logger.info("WhatsApp non configuré — message simulé vers %s", to)
        return False
    url = f"{GRAPH}/{settings.whatsapp_phone_number_id}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text",
               "text": {"preview_url": False, "body": text}}
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    with httpx.Client(timeout=15) as http:
        response = http.post(url, json=payload, headers=headers)
    if response.status_code >= 400:
        logger.error("Envoi WhatsApp refusé : %s", response.text)
    return response.status_code < 400


def send_meta(psid: str, text: str, platform: str = "messenger") -> bool:
    """Messenger et Instagram partagent le même point d'envoi de l'API Graph."""
    if not settings.meta_page_access_token:
        logger.info("Meta non configuré — message simulé vers %s (%s)", psid, platform)
        return False
    url = f"{GRAPH}/me/messages?access_token={settings.meta_page_access_token}"
    with httpx.Client(timeout=15) as http:
        response = http.post(url, json={"recipient": {"id": psid}, "message": {"text": text}})
    if response.status_code >= 400:
        logger.error("Envoi Meta refusé : %s", response.text)
    return response.status_code < 400


def send_email(to: str, text: str, subject: str = "Votre commande") -> bool:
    if not (settings.sales_email and settings.sales_email_app_password):
        logger.info("SMTP non configuré — e-mail simulé vers %s", to)
        return False
    message = EmailMessage()
    message["From"] = settings.sales_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        server.login(settings.sales_email, settings.sales_email_app_password)
        server.send_message(message)
    return True


def dispatch(channel: str, destination: str, text: str) -> bool:
    if channel == "whatsapp":
        return send_whatsapp(destination, text)
    if channel in ("messenger", "instagram"):
        return send_meta(destination, text, channel)
    if channel == "email":
        return send_email(destination, text)
    return False
