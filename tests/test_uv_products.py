import asyncio
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.v1.routes import uv
from backend.core.db.models import Product
from backend.core.db.session import get_session


def test_uv_catalog_only_exposes_reviewed_published_sunscreens():
    engine = create_engine("sqlite://")
    Product.__table__.create(engine)
    with Session(engine) as session:
        for index, changes in enumerate(
            [{}, {"status": "draft"}, {"status": "archived"}, {"reviewed_at": None},
             {"spf": 15}, {"broad_spectrum": False}, {"source_url": None},
             {"category": "moisturizer"}]
        ):
            values = dict(
                brand="Test", name=str(index), category="sunscreen", status="published",
                reviewed_at=datetime.now(UTC), spf=50, broad_spectrum=True,
                source_url=f"https://example.com/{index}", target_skin_types=["dry"],
                water_resistant_minutes=80,
                image_url=f"https://example.com/{index}.jpg",
                concerns=["sensitive-skin"], variant="50 ml", market="US",
            )
            session.add(Product(**(values | changes)))
        session.commit()

        class AsyncSessionAdapter:
            async def scalars(self, query):
                return session.scalars(query)

        products = asyncio.run(uv.sunscreen_products(AsyncSessionAdapter()))
        assert len(products) == 1
        assert products[0]["name"] == "0"
        assert products[0]["target_skin_types"] == ["dry"]
        assert products[0]["water_resistant_minutes"] == 80
        assert products[0]["image_url"] == "https://example.com/0.jpg"
        assert products[0]["suitable_for_sensitive_skin"] is True
        assert products[0]["market"] == "US"
        assert products[0]["variant"] == "50 ml"

    app = FastAPI()
    app.include_router(uv.router)

    class EmptySession:
        async def scalars(self, query):
            class Rows:
                def all(self):
                    return []
            return Rows()

    app.dependency_overrides[get_session] = lambda: EmptySession()
    # Catalog access remains independent of local forecasts and their three-city coverage.
    response = TestClient(app).get("/products")
    assert response.status_code == 200
    assert response.json() == []
