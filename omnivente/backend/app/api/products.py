"""CRUD catalogue produits."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant
from app.core.database import get_db
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["Produits"])


@router.get("", response_model=List[ProductRead])
async def list_products(
    search: str = Query(default=""),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> List[ProductRead]:
    query = select(Product).where(Product.tenant_id == tenant.id).order_by(Product.name)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    return [ProductRead.model_validate(product) for product in result.scalars().all()]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    product = Product(tenant_id=tenant.id, **payload.model_dump())
    if not product.currency:
        product.currency = tenant.currency
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant.id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(product, field, value)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant.id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable.")
    await db.delete(product)
