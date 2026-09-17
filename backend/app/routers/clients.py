"""Répertoire clients, alimenté automatiquement par les conversations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import Client, Message, Order, Tenant
from app.schemas import ClientOut

router = APIRouter(prefix="/api/clients", tags=["Clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    return list(db.scalars(
        select(Client).where(Client.tenant_id == tenant.id).order_by(Client.last_seen_at.desc())
    ))


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db),
                  tenant: Tenant = Depends(get_tenant)):
    """Supprime un client et son historique, sans toucher aux autres tenants."""
    client = db.scalar(select(Client).where(
        Client.id == client_id, Client.tenant_id == tenant.id))
    if client is None:
        raise HTTPException(status_code=404, detail="Client introuvable")

    # Les FK historiques ne sont pas toutes configurées en cascade côté ORM.
    db.query(Message).filter(Message.client_id == client.id).delete(synchronize_session=False)
    db.query(Order).filter(Order.client_id == client.id).delete(synchronize_session=False)
    db.delete(client)
    db.commit()


@router.get("/{client_id}/summary")
def client_summary(client_id: int, db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    total, count = db.execute(
        select(func.coalesce(func.sum(Order.amount), 0), func.count(Order.id))
        .where(Order.tenant_id == tenant.id, Order.client_id == client_id)
    ).one()
    return {"client_id": client_id, "orders": count, "spent": float(total)}
