"""Ingestion des 4 fichiers CSV dans la base PostgreSQL locale.

Usage :
    cd backend
    python -m scripts.seed_db                # ingestion depuis backend/data
    python -m scripts.seed_db --reset        # vide les tables du tenant avant
    python -m scripts.seed_db --data-dir /chemin/vers/csv

Le script cree le tenant "Entreprise D" s'il n'existe pas :
    email    : contact@entreprise-d.tg
    mot de passe : omnivente2026
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

# Permet `python backend/scripts/seed_db.py` comme `python -m scripts.seed_db`.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import AsyncSessionLocal, init_models  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.enums import Channel, ConversationStage, Direction, OrderStatus  # noqa: E402
from app.models.faq import FaqEntry  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.order import Order, OrderItem  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

FILES = {
    "clients": "04_Demandes_Clients_clients.csv",
    "messages": "04_Demandes_Clients_messages.csv",
    "produits": "04_Demandes_Clients_produits.csv",
    "reponses": "04_Demandes_Clients_reponses_existantes.csv",
}

TENANT_EMAIL = "contact@entreprise-d.tg"
TENANT_PASSWORD = "omnivente2026"

# Les CSV peuvent nommer leurs colonnes differemment : on accepte des alias.
ALIASES = {
    "nom": ("nom", "name", "nom_client", "client", "full_name", "libelle", "produit"),
    "telephone": ("telephone", "tel", "phone", "numero", "contact"),
    "email": ("email", "mail", "adresse_email", "e-mail"),
    "canal": ("canal", "channel", "source", "plateforme"),
    "adresse": ("adresse", "address", "rue"),
    "ville": ("ville", "city"),
    "quartier": ("quartier", "district"),
    "client_id": ("client_id", "id_client", "customer_id", "client"),
    "produit_id": ("produit_id", "id_produit", "product_id", "sku"),
    "categorie": ("categorie", "category", "famille", "rayon"),
    "description": ("description", "details", "detail", "resume"),
    "prix": ("prix", "price", "montant", "tarif"),
    "devise": ("devise", "currency"),
    "stock": ("stock", "quantite", "qty", "quantity"),
    "sku": ("sku", "reference", "ref", "code"),
    "message": ("message", "texte", "contenu", "body", "demande"),
    "direction": ("direction", "sens", "type"),
    "date": ("date", "date_message", "created_at", "horodatage", "timestamp"),
    "question": ("question", "demande", "intitule"),
    "reponse": ("reponse", "answer", "reponse_existante", "texte_reponse"),
    "tags": ("tags", "mots_cles", "categorie", "theme"),
}

CHANNEL_MAP = {
    "whatsapp": Channel.WHATSAPP.value,
    "wa": Channel.WHATSAPP.value,
    "instagram": Channel.INSTAGRAM.value,
    "insta": Channel.INSTAGRAM.value,
    "ig": Channel.INSTAGRAM.value,
    "messenger": Channel.MESSENGER.value,
    "facebook": Channel.MESSENGER.value,
    "fb": Channel.MESSENGER.value,
    "email": Channel.EMAIL.value,
    "mail": Channel.EMAIL.value,
}


# ----------------------------------------------------------------------
# Utilitaires CSV
# ----------------------------------------------------------------------
def normalize_key(key: str) -> str:
    return (key or "").strip().lower().replace(" ", "_").replace("-", "_").lstrip("\ufeff")


def pick(row: dict, field: str, default: str = "") -> str:
    for alias in ALIASES.get(field, (field,)):
        if alias in row and str(row[alias]).strip():
            return str(row[alias]).strip()
    return default


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  ! Fichier absent, ignore : {path.name}")
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        rows = []
        for raw in reader:
            rows.append({normalize_key(k): (v or "") for k, v in raw.items() if k})
        return rows


def to_float(value: str) -> float:
    cleaned = (
        str(value)
        .replace("FCFA", "")
        .replace("XOF", "")
        .replace("\u00a0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )
    try:
        return float(cleaned or 0)
    except ValueError:
        return 0.0


def to_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(" ", "") or default))
    except ValueError:
        return default


def to_datetime(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def map_channel(value: str) -> str:
    return CHANNEL_MAP.get((value or "").strip().lower(), Channel.WHATSAPP.value)


# ----------------------------------------------------------------------
# Ingestion
# ----------------------------------------------------------------------
async def get_or_create_tenant(session: AsyncSession) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.email == TENANT_EMAIL))
    ).scalar_one_or_none()
    if tenant:
        print(f"  - Tenant existant reutilise : {tenant.company_name} (id={tenant.id})")
        return tenant

    tenant = Tenant(
        company_name="Entreprise D",
        sector="Vente de marchandises",
        description=(
            "Boutique omnicanale de maroquinerie, habillement et electronique grand public. "
            "Vente par WhatsApp, Instagram, Messenger et email avec retrait en boutique ou livraison."
        ),
        address="Rue des Cocotiers, Tokoin",
        district="Tokoin",
        city="Lome",
        email=TENANT_EMAIL,
        phone="22890000000",
        currency="FCFA",
        hashed_password=hash_password(TENANT_PASSWORD),
    )
    session.add(tenant)
    await session.flush()
    print(f"  + Tenant cree : Entreprise D (id={tenant.id})")
    return tenant


async def reset_tenant_data(session: AsyncSession, tenant_id: int) -> None:
    await session.execute(delete(Message).where(Message.tenant_id == tenant_id))
    await session.execute(delete(Order).where(Order.tenant_id == tenant_id))
    await session.execute(delete(Customer).where(Customer.tenant_id == tenant_id))
    await session.execute(delete(Product).where(Product.tenant_id == tenant_id))
    await session.execute(delete(FaqEntry).where(FaqEntry.tenant_id == tenant_id))
    await session.flush()
    print("  - Donnees precedentes du tenant supprimees.")


async def seed_products(session: AsyncSession, tenant: Tenant, rows: Iterable[dict]) -> dict[str, Product]:
    index: dict[str, Product] = {}
    for row in rows:
        name = pick(row, "nom")
        if not name:
            continue
        product = Product(
            tenant_id=tenant.id,
            sku=pick(row, "sku") or pick(row, "produit_id"),
            name=name,
            category=pick(row, "categorie"),
            description=pick(row, "description"),
            price=to_float(pick(row, "prix", "0")),
            currency=pick(row, "devise", tenant.currency),
            stock=to_int(pick(row, "stock", "0")),
            is_active=True,
        )
        session.add(product)
        await session.flush()
        key = pick(row, "produit_id") or product.sku or name
        index[key] = product
    print(f"  + {len(index)} produits inseres.")
    return index


async def seed_customers(session: AsyncSession, tenant: Tenant, rows: Iterable[dict]) -> dict[str, Customer]:
    index: dict[str, Customer] = {}
    for row in rows:
        name = pick(row, "nom", "Client")
        channel = map_channel(pick(row, "canal"))
        phone = pick(row, "telephone")
        email = pick(row, "email")
        external_ref = email if channel == Channel.EMAIL.value else (phone or email or uuid4().hex[:10])
        customer = Customer(
            tenant_id=tenant.id,
            full_name=name,
            phone=phone,
            email=email,
            channel=channel,
            external_ref=external_ref,
            address=pick(row, "adresse"),
            city=pick(row, "ville"),
            notes=pick(row, "quartier"),
            conversation_stage=ConversationStage.ACCUEIL.value,
        )
        session.add(customer)
        await session.flush()
        index[pick(row, "client_id") or external_ref] = customer
    print(f"  + {len(index)} clients inseres.")
    return index


async def seed_faq(session: AsyncSession, tenant: Tenant, rows: Iterable[dict]) -> int:
    count = 0
    for row in rows:
        question = pick(row, "question")
        answer = pick(row, "reponse")
        if not answer:
            continue
        session.add(
            FaqEntry(
                tenant_id=tenant.id,
                question=question,
                answer=answer,
                tags=pick(row, "tags"),
            )
        )
        count += 1
    await session.flush()
    print(f"  + {count} reponses existantes indexees pour le RAG FAQ.")
    return count


async def seed_messages(
    session: AsyncSession,
    tenant: Tenant,
    rows: Iterable[dict],
    customers: dict[str, Customer],
) -> int:
    count = 0
    fallback = next(iter(customers.values()), None)
    for row in rows:
        body = pick(row, "message")
        if not body:
            continue
        customer = customers.get(pick(row, "client_id")) or fallback
        if customer is None:
            continue
        direction_raw = pick(row, "direction", "inbound").lower()
        direction = (
            Direction.OUTBOUND.value
            if direction_raw.startswith(("out", "sort", "rep"))
            else Direction.INBOUND.value
        )
        created = to_datetime(pick(row, "date"))
        message = Message(
            tenant_id=tenant.id,
            customer_id=customer.id,
            channel=map_channel(pick(row, "canal") or customer.channel),
            direction=direction,
            body=body,
            is_bot=direction == Direction.OUTBOUND.value,
            is_read=direction == Direction.OUTBOUND.value,
        )
        if created:
            message.created_at = created
        session.add(message)
        count += 1
    await session.flush()
    print(f"  + {count} messages importes.")
    return count


async def seed_orders(
    session: AsyncSession,
    tenant: Tenant,
    customers: dict[str, Customer],
    products: dict[str, Product],
) -> int:
    """Cree des commandes de demonstration couvrant tous les statuts."""
    customer_list = list(customers.values())
    product_list = list(products.values())
    if not customer_list or not product_list:
        return 0

    plan = [
        (0, 0, 1, OrderStatus.A_PREPARER),
        (1, 12, 1, OrderStatus.A_PREPARER),
        (2, 4, 1, OrderStatus.EN_LIVRAISON),
        (3, 6, 2, OrderStatus.EN_LIVRAISON),
        (5, 3, 3, OrderStatus.A_PREPARER),
        (8, 8, 1, OrderStatus.RETRAIT_BOUTIQUE),
        (6, 16, 1, OrderStatus.RETRAIT_BOUTIQUE),
        (7, 14, 10, OrderStatus.TERMINE),
        (11, 18, 1, OrderStatus.TERMINE),
        (10, 11, 2, OrderStatus.TERMINE),
        (9, 10, 1, OrderStatus.ANNULE),
    ]

    created = 0
    for customer_idx, product_idx, quantity, statut in plan:
        customer = customer_list[customer_idx % len(customer_list)]
        product = product_list[product_idx % len(product_list)]
        order = Order(
            tenant_id=tenant.id,
            customer_id=customer.id,
            reference=f"CMD-260915-{uuid4().hex[:5].upper()}",
            status=statut.value,
            channel=customer.channel,
            currency=tenant.currency,
            delivery_address=customer.address,
            delivery_note="Commande issue de la conversation client.",
            total_amount=product.price * quantity,
        )
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
            )
        )
        session.add(order)
        created += 1
    await session.flush()
    print(f"  + {created} commandes de demonstration creees.")
    return created


async def main(data_dir: Path, reset: bool) -> None:
    print("OmniVente - ingestion vers PostgreSQL local")
    print(f"Repertoire de donnees : {data_dir}")

    await init_models()
    print("  - Schema verifie (tables creees si absentes).")

    rows = {key: read_csv(data_dir / filename) for key, filename in FILES.items()}

    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_tenant(session)
        if reset:
            await reset_tenant_data(session, tenant.id)

        products = await seed_products(session, tenant, rows["produits"])
        customers = await seed_customers(session, tenant, rows["clients"])
        await seed_faq(session, tenant, rows["reponses"])
        await seed_messages(session, tenant, rows["messages"], customers)
        await seed_orders(session, tenant, customers, products)

        await session.commit()

    print("\nIngestion terminee.")
    print(f"Connexion a l'application : {TENANT_EMAIL} / {TENANT_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion CSV vers PostgreSQL local")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Dossier contenant les 4 CSV")
    parser.add_argument("--reset", action="store_true", help="Vider les donnees du tenant avant ingestion")
    args = parser.parse_args()

    os.chdir(Path(__file__).resolve().parents[1])
    asyncio.run(main(Path(args.data_dir), args.reset))
