"""Boite de reception omnicanale et moteur conversationnel."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant
from app.api.orders import build_reference
from app.core.database import get_db
from app.models.customer import Customer
from app.models.enums import Channel, Direction, OrderStatus
from app.models.faq import FaqEntry
from app.models.message import Message
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.customer import CustomerRead, CustomerUpdate
from app.schemas.message import (
    BotReply,
    ConversationDetail,
    ConversationRead,
    FaqCreate,
    FaqRead,
    IncomingMessage,
    MessageCreate,
    MessageRead,
)
from app.services.bot_ai import SalesBot
from app.services.channels import dispatch
from app.services.rag_faq import FaqDocument

router = APIRouter(tags=["Messagerie"])


# ----------------------------------------------------------------------
# Helpers partages avec les webhooks
# ----------------------------------------------------------------------
async def get_or_create_customer(
    db: AsyncSession,
    tenant: Tenant,
    channel: str,
    external_ref: str,
    full_name: str = "Client",
) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == tenant.id,
            Customer.channel == channel,
            Customer.external_ref == external_ref,
        )
    )
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    customer = Customer(
        tenant_id=tenant.id,
        channel=channel,
        external_ref=external_ref,
        full_name=full_name or "Client",
        phone=external_ref if channel == Channel.WHATSAPP.value else "",
        email=external_ref if channel == Channel.EMAIL.value else "",
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


async def build_bot(db: AsyncSession, tenant: Tenant) -> SalesBot:
    products = (
        await db.execute(
            select(Product).where(Product.tenant_id == tenant.id, Product.is_active.is_(True))
        )
    ).scalars().all()
    faqs = (
        await db.execute(select(FaqEntry).where(FaqEntry.tenant_id == tenant.id))
    ).scalars().all()
    documents = [
        FaqDocument(id=faq.id, question=faq.question, answer=faq.answer, tags=faq.tags)
        for faq in faqs
    ]
    return SalesBot(tenant=tenant, products=list(products), faq_documents=documents)


async def process_incoming(
    db: AsyncSession,
    tenant: Tenant,
    channel: str,
    external_ref: str,
    body: str,
    full_name: str = "Client",
    send_outbound: bool = True,
) -> BotReply:
    """Enregistre le message entrant, calcule la reponse et l'envoie."""
    customer = await get_or_create_customer(db, tenant, channel, external_ref, full_name)

    db.add(
        Message(
            tenant_id=tenant.id,
            customer_id=customer.id,
            channel=channel,
            direction=Direction.INBOUND.value,
            body=body,
            is_read=False,
        )
    )
    await db.flush()

    bot = await build_bot(db, tenant)
    decision = bot.handle(customer, body)

    customer.conversation_stage = decision.stage
    db.add(customer)

    order_id: Optional[int] = None
    if decision.should_create_order and decision.matched_products:
        product = decision.matched_products[0]
        order = Order(
            tenant_id=tenant.id,
            customer_id=customer.id,
            reference=build_reference(),
            status=OrderStatus.A_PREPARER.value,
            channel=channel,
            currency=tenant.currency,
            delivery_address=customer.address,
            delivery_note="Commande creee automatiquement par l'agent conversationnel.",
            total_amount=product.price * decision.quantity,
        )
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=decision.quantity,
                unit_price=product.price,
            )
        )
        db.add(order)
        await db.flush()
        order_id = order.id

    db.add(
        Message(
            tenant_id=tenant.id,
            customer_id=customer.id,
            channel=channel,
            direction=Direction.OUTBOUND.value,
            body=decision.reply,
            is_bot=True,
            is_read=True,
        )
    )
    await db.flush()

    if send_outbound:
        await dispatch(
            channel=channel,
            destination=customer.external_ref or customer.phone or customer.email,
            body=decision.reply,
            subject=f"{tenant.company_name} - votre demande",
        )

    return BotReply(
        reply=decision.reply,
        stage=decision.stage,
        intent=decision.intent,
        order_created=order_id,
    )


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@router.get("/conversations", response_model=List[ConversationRead])
async def list_conversations(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationRead]:
    customers = (
        await db.execute(select(Customer).where(Customer.tenant_id == tenant.id))
    ).scalars().all()

    conversations: List[ConversationRead] = []
    for customer in customers:
        last = (
            await db.execute(
                select(Message)
                .where(Message.customer_id == customer.id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        unread = await db.scalar(
            select(func.count(Message.id)).where(
                Message.customer_id == customer.id,
                Message.direction == Direction.INBOUND.value,
                Message.is_read.is_(False),
            )
        )
        conversations.append(
            ConversationRead(
                customer_id=customer.id,
                full_name=customer.full_name,
                channel=customer.channel,
                external_ref=customer.external_ref,
                stage=customer.conversation_stage,
                last_message=(last.body[:120] if last else ""),
                last_message_at=(last.created_at if last else None),
                unread=int(unread or 0),
            )
        )
    conversations.sort(key=lambda c: (c.last_message_at is None, c.last_message_at), reverse=True)
    return conversations


@router.get("/conversations/{customer_id}", response_model=ConversationDetail)
async def conversation_detail(
    customer_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    customer = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    messages = (
        await db.execute(
            select(Message)
            .where(Message.customer_id == customer.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
    ).scalars().all()

    await db.execute(
        update(Message)
        .where(Message.customer_id == customer.id, Message.direction == Direction.INBOUND.value)
        .values(is_read=True)
    )

    return ConversationDetail(
        customer_id=customer.id,
        full_name=customer.full_name,
        channel=customer.channel,
        stage=customer.conversation_stage,
        messages=[MessageRead.model_validate(message) for message in messages],
    )


@router.post("/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_manual_message(
    payload: MessageCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    """Reponse ecrite manuellement par un agent humain depuis la boite de reception."""
    customer = (
        await db.execute(
            select(Customer).where(
                Customer.id == payload.customer_id, Customer.tenant_id == tenant.id
            )
        )
    ).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    channel = payload.channel.value if payload.channel else customer.channel
    message = Message(
        tenant_id=tenant.id,
        customer_id=customer.id,
        channel=channel,
        direction=payload.direction.value,
        body=payload.body,
        is_bot=payload.is_bot,
        is_read=True,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    if payload.direction == Direction.OUTBOUND:
        await dispatch(
            channel=channel,
            destination=customer.external_ref or customer.phone or customer.email,
            body=payload.body,
            subject=f"{tenant.company_name} - votre demande",
        )
    return MessageRead.model_validate(message)


@router.post("/messages/incoming", response_model=BotReply)
async def simulate_incoming(
    payload: IncomingMessage,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> BotReply:
    """Simule un message client (utile pour tester le bot depuis l'interface)."""
    return await process_incoming(
        db=db,
        tenant=tenant,
        channel=payload.channel.value,
        external_ref=payload.external_ref,
        body=payload.body,
        full_name=payload.full_name,
        send_outbound=False,
    )


@router.get("/customers", response_model=List[CustomerRead])
async def list_customers(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[CustomerRead]:
    result = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant.id).order_by(Customer.full_name)
    )
    return [CustomerRead.model_validate(customer) for customer in result.scalars().all()]


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> CustomerRead:
    customer = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(customer, field, value)
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return CustomerRead.model_validate(customer)


@router.get("/faq", response_model=List[FaqRead])
async def list_faq(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[FaqRead]:
    result = await db.execute(select(FaqEntry).where(FaqEntry.tenant_id == tenant.id))
    return [FaqRead.model_validate(entry) for entry in result.scalars().all()]


@router.post("/faq", response_model=FaqRead, status_code=status.HTTP_201_CREATED)
async def create_faq(
    payload: FaqCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> FaqRead:
    entry = FaqEntry(tenant_id=tenant.id, **payload.model_dump())
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return FaqRead.model_validate(entry)
