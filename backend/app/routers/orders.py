"""Commandes : liste par statut et changement d'étape depuis le tableau de bord."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_tenant
from app.models import ORDER_STATUSES, Message, Order, Tenant
from app.schemas import OrderOut, OrderStatusIn
from app.services import channels

router = APIRouter(prefix="/api/orders", tags=["Commandes"])


@router.get("", response_model=list[OrderOut])
def list_orders(status: str | None = None, db: Session = Depends(get_db),
                tenant: Tenant = Depends(get_tenant)):
    query = (select(Order)
             .options(joinedload(Order.client), joinedload(Order.product))
             .where(Order.tenant_id == tenant.id)
             .order_by(Order.created_at.desc()))
    if status:
        if status not in ORDER_STATUSES:
            raise HTTPException(422, f"Statut inconnu. Valeurs acceptées : {', '.join(ORDER_STATUSES)}")
        query = query.where(Order.status == status)
    return list(db.scalars(query))


@router.get("/board")
def board(db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    """Commandes regroupées par statut, prêtes à alimenter les grilles du tableau de bord."""
    orders = db.scalars(
        select(Order)
        .options(joinedload(Order.client), joinedload(Order.product))
        .where(Order.tenant_id == tenant.id)
        .order_by(Order.created_at.desc())
    )
    grouped: dict[str, list] = {status: [] for status in ORDER_STATUSES}
    for order in orders:
        grouped[order.status].append(OrderOut.model_validate(order))
    return grouped


@router.patch("/{reference}", response_model=OrderOut)
def update_status(reference: str, payload: OrderStatusIn,
                  db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    order = db.scalar(
        select(Order)
        .options(joinedload(Order.client), joinedload(Order.product))
        .where(Order.tenant_id == tenant.id, Order.reference == reference)
    )
    if order is None:
        raise HTTPException(404, f"Commande {reference} introuvable.")
    allowed = {
        "preparer": {"livraison"} if order.fulfilment == "livraison" else {"retrait"},
        "livraison": {"livre"},
        "livre": {"termine"},
        "retrait": {"termine"},
        "termine": set(),
        "probleme": set(),
    }
    if payload.status != order.status and payload.status not in allowed.get(order.status, set()):
        raise HTTPException(
            422,
            "Transition impossible : une commande terminée ne peut pas revenir en arrière."
            if order.status == "termine"
            else "Cette commande doit suivre l'étape suivante prévue pour son mode de remise.",
        )
    if payload.status == order.status:
        return order
    order.status = payload.status
    db.commit()
    pickup_point = tenant.pickup_point or "notre boutique"
    messages = {
        "retrait": (
            f"Votre commande {order.reference} est prête à être retirée à {pickup_point}. "
            f"Vous pouvez passer {order.slot or 'au jour et à l’heure convenus'} "
            "pour récupérer votre produit."
        ),
        "livraison": (
            f"Votre commande {order.reference} a été remise au livreur. "
            f"Soyez prêt(e) à {order.slot or 'la date et l’heure convenues'} "
            f"à la localisation indiquée ({order.place or 'dans le lieu communiqué'}) "
            "pour récupérer votre colis auprès du livreur."
        ),
        "livre": (
            f"Votre commande {order.reference} a été livrée. "
            "Merci de confirmer la bonne réception auprès du livreur."
        ),
        "termine": (
            "Merci d’avoir fait confiance à notre boutique. "
            "Nous espérons vous revoir bientôt."
        ),
    }
    subjects = {
        "retrait": "Votre commande est prête à la boutique",
        "livraison": "Votre commande a été remise au livreur",
        "livre": "Votre commande a été livrée",
        "termine": "Merci pour votre confiance",
    }
    body = messages.get(payload.status)
    if body:
        db.add(Message(
            tenant_id=tenant.id,
            client_id=order.client_id,
            channel=order.channel,
            direction="out",
            body=body,
            step="commande",
        ))
        db.commit()
        destination = order.client.phone or order.client.email or order.client.external_id
        channels.dispatch(
            order.channel,
            destination,
            body,
            (tenant.integrations or {}).get(order.channel)
            or (tenant.integrations or {}).get("meta"),
            subject=subjects.get(payload.status, "Mise à jour de votre commande"),
        )
    return order
