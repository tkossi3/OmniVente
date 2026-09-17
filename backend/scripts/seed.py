"""Création des tables et import du catalogue CSV du Hackathon LSC 2026.

    python -m scripts.seed           # tables + commerçant + catalogue
    python -m scripts.seed --demo    # ajoute des conversations et commandes de démonstration
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Client, Message, Order, Product, Tenant  # noqa: E402
from app.services.state_machine import new_session  # noqa: E402

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "products.csv"
CLIENTS_CSV_PATH = Path(__file__).resolve().parents[2] / "Docs" / "04_Demandes_Clients_clients.csv"

TENANT = dict(
    slug="kino-steak", company="Tinos TechLogistics", sector="Distribution & logistique",
    legal_form="SARL", tax_id="1000487621",
    manager="Afi Kinvi", phone="+228 90 00 11 22", email="ventes@kinosteak.tg",
    website="kinosteak.tg",
    address="142, rue des Hydrocarbures, Tokoin", city="Lomé", country="Togo", currency="FCFA",
    pickup_point="Boutique Tokoin, en face de la station CAP",
    delivery_zone="Lomé et périphérie · livraison sous 24 h",
    opening_hours="Lun–Sam · 08h00 – 19h00",
    about=("Tinos TechLogistics distribue des packs de produits et services logistiques "
           "aux commerçants et PME du Grand Lomé."),
)

DEMO_CLIENTS = [
    ("Afiwa Segbedji", "whatsapp", "22890441207"),
    ("Komlan Adjaho", "instagram", "17841400000001"),
    ("Sena Aziaka", "messenger", "6512345678901"),
    ("Mawuli Dossou", "email", "mawuli.dossou@example.tg"),
]

DEMO_ORDERS = [
    ("P02", 2, "whatsapp", "preparer", "livraison", "Jeudi 18 sept. · 14h00", "Bè-Kpota, Lomé · 6.1319, 1.2492"),
    ("P04", 1, "instagram", "preparer", "retrait", "Jeudi 18 sept. · 10h30", "Boutique Tokoin"),
    ("P08", 1, "messenger", "livraison", "livraison", "Aujourd'hui · 16h00", "Adidogomé, Lomé · 6.1962, 1.1871"),
    ("P07", 1, "email", "retrait", "retrait", "Vendredi 19 sept. · 09h00", "Boutique Tokoin"),
    ("P01", 5, "whatsapp", "termine", "retrait", "Lundi 15 sept. · 12h00", "Boutique Tokoin"),
]


def upsert_tenant(db) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == TENANT["slug"]))
    if tenant is None:
        tenant = Tenant(**TENANT, integrations={})
        db.add(tenant)
        db.flush()
        print(f"  · commerçant créé : {tenant.company}")
    else:
        for key, value in TENANT.items():
            if key != "slug":
                setattr(tenant, key, value)
        print(f"  · commerçant déjà présent : {tenant.company}")
    return tenant


def import_catalog(db, tenant: Tenant) -> int:
    imported = 0
    with CSV_PATH.open(encoding="utf-8") as handle:
        for position, row in enumerate(csv.DictReader(handle), start=1):
            product = db.scalar(select(Product).where(
                Product.tenant_id == tenant.id, Product.ref == row["ref"]))
            quantity = int(row["quantity"])
            values = dict(position=position, name=row["name"], price=float(row["price"]),
                          quantity=quantity, in_stock=row["stock_status"].strip().lower() == "en stock"
                          and quantity > 0, category=row["category"])
            if product is None:
                db.add(Product(tenant_id=tenant.id, ref=row["ref"], **values))
                imported += 1
            else:
                for key, value in values.items():
                    setattr(product, key, value)
    db.flush()
    return imported


def import_clients(db, tenant: Tenant) -> int:
    imported = 0
    channels = ("whatsapp", "instagram", "messenger", "email")
    with CLIENTS_CSV_PATH.open(encoding="utf-8-sig") as handle:
        for position, row in enumerate(csv.DictReader(handle)):
            channel = channels[position % len(channels)]
            client = db.scalar(select(Client).where(
                Client.tenant_id == tenant.id,
                Client.channel == channel,
                Client.external_id == row["client_id"]))
            values = dict(name=row["nom"], location=row["ville"])
            if client is None:
                client = Client(tenant_id=tenant.id, channel=channel,
                                external_id=row["client_id"], session_state={},
                                **values)
                db.add(client)
                imported += 1
            else:
                for key, value in values.items():
                    setattr(client, key, value)
    db.flush()
    return imported


def seed_demo(db, tenant: Tenant) -> None:
    clients = []
    for name, channel, external_id in DEMO_CLIENTS:
        client = db.scalar(select(Client).where(
            Client.tenant_id == tenant.id, Client.channel == channel,
            Client.external_id == external_id))
        if client is None:
            client = Client(tenant_id=tenant.id, name=name, channel=channel,
                            external_id=external_id, session_state=new_session(),
                            phone=external_id if channel == "whatsapp" else None,
                            email=external_id if channel == "email" else None)
            db.add(client)
            db.flush()
        clients.append(client)

    if db.scalar(select(Order).where(Order.tenant_id == tenant.id)) is not None:
        print("  · commandes de démonstration déjà présentes")
        return

    for index, (ref, quantity, channel, status, fulfilment, slot, place) in enumerate(DEMO_ORDERS):
        product = db.scalar(select(Product).where(
            Product.tenant_id == tenant.id, Product.ref == ref))
        client = clients[index % len(clients)]
        db.add(Order(tenant_id=tenant.id, client_id=client.id, product_id=product.id,
                     reference=f"CMD-2026-{index + 1:03d}", quantity=quantity,
                     amount=float(product.price) * quantity, channel=channel, status=status,
                     fulfilment=fulfilment, slot=slot, place=place,
                     created_at=datetime.now() - timedelta(days=index)))
        db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=channel,
                       direction="in", body=str(index + 1), step="catalogue",
                       created_at=datetime.now() - timedelta(days=index, minutes=6)))
        db.add(Message(tenant_id=tenant.id, client_id=client.id, channel=channel,
                       direction="out", body=f"Commande enregistrée : {quantity} × {product.name}.",
                       step="fin", created_at=datetime.now() - timedelta(days=index, minutes=5)))
    print(f"  · {len(DEMO_ORDERS)} commandes de démonstration créées")


def run(demo: bool = False) -> None:
    """Crée les tables si besoin, importe le catalogue, et ajoute un jeu de
    démonstration si demandé. Idempotent : peut être rappelée sans risque
    (utilisé par AUTO_SEED au démarrage de l'application)."""
    print("OmniVente — initialisation des données")
    Base.metadata.create_all(engine)
    print("  · tables vérifiées")
    with SessionLocal() as db:
        tenant = upsert_tenant(db)
        count = import_catalog(db, tenant)
        print(f"  · catalogue importé depuis {CSV_PATH.name} ({count} nouvelles références)")
        count = import_clients(db, tenant)
        print(f"  · clients importés depuis {CLIENTS_CSV_PATH.name} ({count} nouveaux clients)")
        if demo:
            seed_demo(db, tenant)
        db.commit()
    print("Terminé.")


def main() -> None:
    run(demo="--demo" in sys.argv)


if __name__ == "__main__":
    main()
