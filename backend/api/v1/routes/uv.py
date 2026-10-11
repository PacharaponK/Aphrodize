from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.db.models import Product
from backend.core.db.session import get_session
from backend.services.uv_map_service import load_map
from backend.services.uv_service import load_recommendation

router = APIRouter()
City = Literal["bangkok", "songkhla", "chiang_mai"]


@router.get("/map")
async def uv_map(
    day: Literal["today", "tomorrow"] = Query("today"),
    source: Literal["api", "model"] = Query("api"),
) -> dict:
    return load_map(day, source=source)


@router.get("/recommendation")
async def recommendation(
    city: City = Query(...), session: AsyncSession = Depends(get_session)
) -> dict:
    try:
        result = load_recommendation(city)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    result["products"] = (await sunscreen_products(session))[:5]
    return result


@router.get("/products")
async def sunscreen_products(session: AsyncSession = Depends(get_session)) -> list[dict]:
    # ponytail: bounded reviewed catalog; add pagination when it exceeds 500 items.
    products = (
        await session.scalars(
            select(Product)
            .where(
                Product.category == "sunscreen",
                Product.status == "published",
                Product.reviewed_at.is_not(None),
                Product.spf >= 30,
                Product.broad_spectrum.is_(True),
                Product.source_url.is_not(None),
            )
            .order_by(Product.brand, Product.name)
            .limit(500)
        )
    ).all()
    return [
        {
            "brand": product.brand,
            "name": product.name,
            "variant": product.variant,
            "market": product.market,
            "spf": product.spf,
            "broad_spectrum": product.broad_spectrum,
            "water_resistant_minutes": product.water_resistant_minutes,
            "source_url": product.source_url,
            "image_url": product.image_url,
            "target_skin_types": product.target_skin_types,
            "suitable_for_sensitive_skin": "sensitive-skin" in (product.concerns or []),
        }
        for product in products
    ]
