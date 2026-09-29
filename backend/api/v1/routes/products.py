from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.product import ProductInput, ProductRead, ProductStatusInput
from backend.core.db.models import Product
from backend.core.db.session import get_session

router = APIRouter()


def require_publishable(product: Product) -> None:
    if not all(
        (
            product.price_satang is not None,
            product.ingredients_label,
            product.ingredients_inci,
            product.target_skin_types,
            product.source_url,
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Price, label ingredients, reviewed INCI ingredients, skin types, and source URL are required",
        )


@router.get("", response_model=list[ProductRead])
async def list_products(session: AsyncSession = Depends(get_session)) -> list[Product]:
    # ponytail: one bounded admin catalog view; add pagination when the catalog grows past 500 items.
    query = select(Product).order_by(Product.created_at.desc()).limit(500)
    return list((await session.scalars(query)).all())


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductInput, session: AsyncSession = Depends(get_session)
) -> Product:
    product = Product(**payload.model_dump(), status="draft")
    if product.price_satang is not None:
        product.price_checked_at = datetime.now(UTC)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID, payload: ProductInput, session: AsyncSession = Depends(get_session)
) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    old_price = product.price_satang
    for field, value in payload.model_dump().items():
        setattr(product, field, value)
    if old_price != product.price_satang:
        product.price_checked_at = datetime.now(UTC) if product.price_satang is not None else None
    if product.status == "published":
        product.status = "draft"
        product.reviewed_at = None
    await session.commit()
    await session.refresh(product)
    return product


@router.patch("/{product_id}/status", response_model=ProductRead)
async def set_product_status(
    product_id: UUID, payload: ProductStatusInput, session: AsyncSession = Depends(get_session)
) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.status == "published":
        require_publishable(product)
        product.reviewed_at = datetime.now(UTC)
    elif payload.status == "draft":
        product.reviewed_at = None
    product.status = payload.status
    await session.commit()
    await session.refresh(product)
    return product
