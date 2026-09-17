"""Catalogue : consultation et mise à jour du stock."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_tenant
from app.models import Product, Tenant
from app.schemas import ProductOut

router = APIRouter(prefix="/api/products", tags=["Catalogue"])


class StockIn(BaseModel):
    quantity: int


def catalog_for(db: Session, tenant: Tenant) -> list[Product]:
    return list(db.scalars(
        select(Product).where(Product.tenant_id == tenant.id).order_by(Product.position)
    ))


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    return catalog_for(db, tenant)


@router.patch("/{ref}/stock", response_model=ProductOut)
def update_stock(ref: str, payload: StockIn,
                 db: Session = Depends(get_db), tenant: Tenant = Depends(get_tenant)):
    product = db.scalar(select(Product).where(Product.tenant_id == tenant.id, Product.ref == ref))
    if product is None:
        raise HTTPException(404, f"Référence {ref} introuvable.")
    product.quantity = max(0, payload.quantity)
    product.in_stock = product.quantity > 0
    db.commit()
    return product
