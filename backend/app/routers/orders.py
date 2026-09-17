"""Commandes : liste par statut et changement d'étape depuis le tableau de bord."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_tenant
from app.models import ORDER_STATUSES, Order, Tenant
from app.schemas import OrderOut, OrderStatusIn

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
    order.status = payload.status
    db.commit()
    return order
