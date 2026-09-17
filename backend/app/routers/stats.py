"""Indicateurs du tableau de bord."""
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import CHANNELS, ORDER_STATUSES, Message, Order, Tenant
from app.schemas import StatsOut

router = APIRouter(prefix="/api/stats", tags=["Statistiques"])
JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


@router.get("", response_model=StatsOut)
def dashboard(db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    rows = db.execute(
        select(Order.status, func.count(Order.id), func.coalesce(func.sum(Order.amount), 0))
        .where(Order.tenant_id == tenant.id).group_by(Order.status)
    ).all()
    by_status = {status: 0 for status in ORDER_STATUSES}
    revenue = 0.0
    total = 0
    for status, count, amount in rows:
        by_status[status] = count
        total += count
        if status != "probleme":
            revenue += float(amount)

    by_channel = {
        channel: float(amount) for channel, amount in db.execute(
            select(Order.channel, func.coalesce(func.sum(Order.amount), 0))
            .where(Order.tenant_id == tenant.id, Order.status != "probleme")
            .group_by(Order.channel)
        ).all()
    }

    since = datetime.now() - timedelta(days=6)
    counters: dict[str, list[int]] = {c: [0] * 7 for c in CHANNELS}
    labels = [(since + timedelta(days=i)).strftime("%a")[:3].capitalize() for i in range(7)]
    rows = db.execute(
        select(Message.channel, func.date(Message.created_at), func.count(Message.id))
        .where(Message.tenant_id == tenant.id, Message.created_at >= since,
               Message.direction == "in")
        .group_by(Message.channel, func.date(Message.created_at))
    ).all()
    index = {(since + timedelta(days=i)).date(): i for i in range(7)}
    for channel, day, count in rows:
        slot = index.get(day)
        if slot is not None and channel in counters:
            counters[channel][slot] = count

    return StatsOut(revenue=revenue, orders_total=total, orders_by_status=by_status,
                    revenue_by_channel=by_channel, messages_by_channel=counters, days=labels)
