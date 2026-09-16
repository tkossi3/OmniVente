"""Commandes : creation, mise a jour de statut, vue swimlanes et statistiques."""
from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_tenant
from app.core.database import get_db
from app.models.customer import Customer
from app.models.enums import ORDER_STATUS_LABELS, OrderStatus
from app.models.message import Message
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.order import (
    DashboardStats,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
    OrderUpdate,
    SwimlaneColumn,
)

router = APIRouter(prefix="/orders", tags=["Commandes"])


def build_reference() -> str:
    stamp = datetime.now(timezone.utc).strftime("%y%m%d")
    return f"CMD-{stamp}-{uuid4().hex[:5].upper()}"


def to_read(order: Order, customer_name: str = "") -> OrderRead:
    data = OrderRead.model_validate(order)
    # `customer` n'est lu que s'il a deja ete charge (selectinload), pour eviter
    # tout chargement paresseux dans un contexte asynchrone.
    loaded_customer = order.__dict__.get("customer")
    data.customer_name = customer_name or (
        loaded_customer.full_name if loaded_customer is not None else ""
    )
    return data


async def load_orders(db: AsyncSession, tenant_id: int) -> List[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.tenant_id == tenant_id)
        .options(selectinload(Order.items), selectinload(Order.customer))
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("", response_model=List[OrderRead])
async def list_orders(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[OrderRead]:
    return [to_read(order) for order in await load_orders(db, tenant.id)]


@router.get("/swimlanes", response_model=List[SwimlaneColumn])
async def swimlanes(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[SwimlaneColumn]:
    """Une bande horizontale par statut, dans l'ordre du cycle de vie."""
    orders = await load_orders(db, tenant.id)
    lanes: List[SwimlaneColumn] = []
    for statut in OrderStatus:
        bucket = [to_read(order) for order in orders if order.status == statut.value]
        lanes.append(
            SwimlaneColumn(
                status=statut.value,
                label=ORDER_STATUS_LABELS[statut.value],
                count=len(bucket),
                orders=bucket,
            )
        )
    return lanes


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    customer_result = await db.execute(
        select(Customer).where(
            Customer.id == payload.customer_id, Customer.tenant_id == tenant.id
        )
    )
    customer = customer_result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    order = Order(
        tenant_id=tenant.id,
        customer_id=customer.id,
        reference=build_reference(),
        status=payload.status.value,
        channel=payload.channel.value,
        currency=tenant.currency,
        delivery_address=payload.delivery_address or customer.address,
        delivery_note=payload.delivery_note,
    )

    total = 0.0
    for item in payload.items:
        unit_price = item.unit_price
        product_name = item.product_name
        if item.product_id:
            product_result = await db.execute(
                select(Product).where(
                    Product.id == item.product_id, Product.tenant_id == tenant.id
                )
            )
            product = product_result.scalar_one_or_none()
            if product is not None:
                unit_price = unit_price or product.price
                product_name = product_name or product.name
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                product_name=product_name or "Article",
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )
        total += unit_price * item.quantity

    order.total_amount = total
    db.add(order)
    await db.flush()
    await db.refresh(order, attribute_names=["items"])
    return to_read(order, customer.full_name)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_status(
    order_id: int,
    payload: OrderStatusUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items), selectinload(Order.customer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    order.status = payload.status.value
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return to_read(order)


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant.id)
        .options(selectinload(Order.items), selectinload(Order.customer))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") is not None:
        order.status = data["status"].value
    if data.get("delivery_address") is not None:
        order.delivery_address = data["delivery_address"]
    if data.get("delivery_note") is not None:
        order.delivery_note = data["delivery_note"]
    db.add(order)
    await db.flush()
    await db.refresh(order)
    return to_read(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    await db.delete(order)


@router.get("/stats", response_model=DashboardStats)
async def stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    orders = await load_orders(db, tenant.id)

    by_status: Dict[str, int] = {statut.value: 0 for statut in OrderStatus}
    by_channel: Dict[str, int] = {}
    revenue = 0.0
    for order in orders:
        by_status[order.status] = by_status.get(order.status, 0) + 1
        by_channel[order.channel] = by_channel.get(order.channel, 0) + 1
        if order.status != OrderStatus.ANNULE.value:
            revenue += order.total_amount

    customers_total = await db.scalar(
        select(func.count(Customer.id)).where(Customer.tenant_id == tenant.id)
    )
    messages_unread = await db.scalar(
        select(func.count(Message.id)).where(
            Message.tenant_id == tenant.id,
            Message.direction == "inbound",
            Message.is_read.is_(False),
        )
    )

    open_statuses = {
        OrderStatus.A_PREPARER.value,
        OrderStatus.EN_LIVRAISON.value,
        OrderStatus.RETRAIT_BOUTIQUE.value,
    }
    return DashboardStats(
        orders_total=len(orders),
        orders_open=sum(1 for order in orders if order.status in open_statuses),
        revenue=round(revenue, 2),
        currency=tenant.currency,
        customers_total=int(customers_total or 0),
        messages_unread=int(messages_unread or 0),
        by_channel=by_channel,
        by_status=by_status,
    )
