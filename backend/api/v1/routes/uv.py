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
            .limit(5)
        )
    ).all()
    result["products"] = [
        {
            "brand": product.brand,
            "name": product.name,
            "spf": product.spf,
            "broad_spectrum": product.broad_spectrum,
            "water_resistant_minutes": product.water_resistant_minutes,
            "source_url": product.source_url,
        }
        for product in products
    ]
    return result
