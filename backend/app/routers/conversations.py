"""Orchestration du dialogue : webhooks et simulateur passent tous par ici.

    message entrant → client → catalogue → machine d'état → réponse
                                                  ↓
                                         création de la commande
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import Client, Message, Order, Product, Tenant
from app.schemas import ChatIn, ChatOut, MessageOut
from app.services import groq_client, state_machine

router = APIRouter(prefix="/api", tags=["Conversations"])


def _catalog(db: Session, tenant: Tenant) -> list[dict]:
    products = db.scalars(
        select(Product).where(Product.tenant_id == tenant.id).order_by(Product.position)
    )
    return [{"position": p.position, "ref": p.ref, "name": p.name, "price": float(p.price),
             "quantity": p.quantity, "in_stock": p.in_stock} for p in products]


def _shop(tenant: Tenant) -> dict:
    return {"company": tenant.company, "address": tenant.address, "city": tenant.city,
            "opening_hours": tenant.opening_hours, "pickup_point": tenant.pickup_point,
            "delivery_zone": tenant.delivery_zone, "about": tenant.about}


def _get_or_create_client(db: Session, tenant: Tenant, channel: str, external_id: str,
                          name: str) -> Client:
    client = db.scalar(select(Client).where(
        Client.tenant_id == tenant.id, Client.channel == channel,
        Client.external_id == external_id))
    if client is None:
        client = Client(tenant_id=tenant.id, channel=channel, external_id=external_id,
                        name=name or "Client", session_state={},
                        phone=external_id if channel in ("whatsapp",) else None,
                        email=external_id if channel == "email" else None)
        db.add(client)
        db.flush()
    client.last_seen_at = datetime.now()
    return client


def _next_reference(db: Session, tenant: Tenant) -> str:
    year = datetime.now().year
    count = db.scalar(select(func.count(Order.id)).where(Order.tenant_id == tenant.id)) or 0
    return f"CMD-{year}-{count + 1:03d}"


def _expected_options(step: str, catalog: list[dict]) -> tuple[str, int, int]:
    """Bornes attendues par étape, transmises à Groq pour lever les ambiguïtés."""
    if step == "catalogue":
        return ("\n".join(f"{p['position']} - {p['name']}" for p in catalog), 1, len(catalog))
    if step == "quantite":
        return ("Une quantité en chiffres", 1, 99)
    if step == "mode":
        return ("1 - Livraison à domicile\n2 - Retrait en boutique", 1, 2)
    if step == "validation":
        return ("1 - Confirmer\n2 - Modifier", 1, 2)
    return ("", 1, 99)


def _needs_human(text: str) -> bool:
    markers = (
        "vendeur", "responsable", "conseiller", "humain", "compliqué", "complexe",
        "sur mesure", "offre entreprise", "réclamation", "remboursement", "litige",
        "problème", "plainte", "rappeler",
    )
    normalized = text.lower()
    return any(marker in normalized for marker in markers)


def process_incoming(db: Session, tenant: Tenant, payload: ChatIn) -> ChatOut:
    client = _get_or_create_client(db, tenant, payload.channel, payload.external_id, payload.name)
    catalog = _catalog(db, tenant)
    shop = _shop(tenant)

    db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                   direction="in", body=payload.text,
                   step=client.session_state.get("step") if client.session_state else None))

    # Première prise de contact : salutation et catalogue numéroté.
    if not client.session_state:
        client.session_state = state_machine.new_session()
        reply = state_machine.greeting(client.name, shop, catalog)
        db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                       direction="out", body=reply.text, step=reply.step))
        db.commit()
        return ChatOut(reply=reply.text, step=reply.step, quick_replies=reply.quick)

    session = dict(client.session_state)
    step = session.get("step", "catalogue")
    options, low, high = _expected_options(step, catalog)
    choice = None
    if step in ("catalogue", "quantite", "mode", "validation") and _needs_human(payload.text):
        session["step"] = "humain"
        session["previous_step"] = step
        client.session_state = session
        reply = ("Je transmets votre demande à un vendeur. "
                 "Un membre de notre équipe va vous répondre ici rapidement.")
        db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                       direction="out", body=reply, step="humain"))
        db.commit()
        return ChatOut(reply=reply, step="humain")
    if step in ("catalogue", "quantite", "mode", "validation"):
        choice = groq_client.extract_number(payload.text, options, low, high)
        if choice is None and groq_client.is_enabled():
            # Le client pose une question hors parcours : Groq répond, puis on relance l'étape.
            aside = groq_client.answer_off_script(payload.text, shop, catalog)
            if aside:
                db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                               direction="out", body=aside, step=step))
                db.commit()
                return ChatOut(reply=aside, step=step,
                               quick_replies=[str(p["position"]) for p in catalog[:5]])
        if choice is None and not groq_client.is_enabled():
            session["step"] = "humain"
            session["previous_step"] = step
            client.session_state = session
            reply = ("Votre demande nécessite l'intervention d'un vendeur. "
                     "Un membre de notre équipe va vous répondre ici rapidement.")
            db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                           direction="out", body=reply, step="humain"))
            db.commit()
            return ChatOut(reply=reply, step="humain")

    session, reply = state_machine.advance(session, payload.text, catalog, shop, choice)
    reference = None

    if reply.order:
        product = db.scalar(select(Product).where(
            Product.tenant_id == tenant.id, Product.ref == reply.order["product_ref"]))
        reference = _next_reference(db, tenant)
        db.add(Order(tenant_id=tenant.id, client_id=client.id, product_id=product.id,
                     reference=reference, quantity=reply.order["quantity"],
                     amount=reply.order["amount"], channel=payload.channel, status="preparer",
                     fulfilment=reply.order["fulfilment"], slot=reply.order["slot"],
                     place=reply.order["place"]))
        product.quantity = max(0, product.quantity - reply.order["quantity"])
        product.in_stock = product.quantity > 0
        if reply.order["fulfilment"] == "livraison":
            client.location = reply.order["place"]
        reply.text = reply.text.replace("Votre commande est confirmée",
                                        f"Votre commande {reference} est confirmée")

    client.session_state = session
    db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=payload.channel,
                   direction="out", body=reply.text, step=reply.step))
    db.commit()
    return ChatOut(reply=reply.text, step=reply.step, quick_replies=reply.quick,
                   order_reference=reference)


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn, db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    """Point d'entrée unique du dialogue, utilisé aussi par le simulateur du tableau de bord."""
    return process_incoming(db, tenant, payload)


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    clients = db.scalars(select(Client).where(Client.tenant_id == tenant.id)
                         .order_by(Client.last_seen_at.desc()))
    result = []
    for client in clients:
        last = db.scalar(select(Message).where(Message.client_id == client.id)
                         .order_by(Message.created_at.desc()).limit(1))
        result.append({"client_id": client.id, "name": client.name, "channel": client.channel,
                       "step": (client.session_state or {}).get("step"),
                       "preview": last.body.splitlines()[0] if last else "",
                       "last_seen_at": client.last_seen_at})
    return result


@router.get("/conversations/{client_id}/messages", response_model=list[MessageOut])
def conversation_messages(client_id: int, db: Session = Depends(get_db),
                          tenant: Tenant = Depends(get_tenant)):
    return list(db.scalars(
        select(Message).where(Message.tenant_id == tenant.id, Message.client_id == client_id)
        .order_by(Message.created_at)
    ))


@router.post("/conversations/{client_id}/reset")
def reset_conversation(client_id: int, db: Session = Depends(get_db),
                       tenant: Tenant = Depends(get_tenant)):
    client = db.get(Client, client_id)
    if client and client.tenant_id == tenant.id:
        client.session_state = state_machine.new_session()
        db.commit()
    return {"status": "reset"}


@router.post("/conversations/{client_id}/reply")
def seller_reply(client_id: int, payload: dict, db: Session = Depends(get_db),
                 tenant: Tenant = Depends(get_tenant)):
    """Publie une réponse du vendeur et rend la main à l'agent."""
    client = db.scalar(select(Client).where(
        Client.id == client_id, Client.tenant_id == tenant.id))
    text = str(payload.get("text", "")).strip()
    if client is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Client introuvable")
    if not text:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="La réponse ne peut pas être vide")

    session = dict(client.session_state or {})
    previous_step = session.pop("previous_step", "catalogue")
    session["step"] = previous_step
    client.session_state = session
    client.last_seen_at = datetime.now()
    db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=client.channel,
                   direction="out", body=text, step="vendeur"))
    db.commit()
    return {"status": "sent", "step": previous_step}
