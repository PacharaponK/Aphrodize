from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.core.db.models import Product
from backend.services.fixture_service import load_products, products_from_fixture

FIXTURE = Path(__file__).resolve().parents[1] / 'backend/fixtures/sunscreens-2026-10-08.yaml'


async def test_sunscreen_batch_is_valid_repeatable_and_keeps_existing_edits():
    products = products_from_fixture(FIXTURE)
    assert len(products) == 8
    assert sum(p.water_resistant_minutes == 80 for p in products) == 5
    assert all(p.image_url and p.market == 'US' for p in products)
    assert all('sensitive-skin' in p.concerns for p in products)
    engine = create_engine('sqlite://')
    Product.__table__.create(engine)
    with Session(engine) as session:
        class Adapter:
            async def scalar(self, query):
                return session.scalar(query)

            def add(self, product):
                session.add(product)

            async def commit(self):
                session.commit()

        adapter = Adapter()
        assert await load_products(FIXTURE, adapter) == 8
        existing = session.scalar(select(Product).limit(1))
        existing.status = 'archived'
        existing.name = 'Admin edit'
        session.commit()
        assert await load_products(FIXTURE, adapter) == 0
        assert existing.status == 'archived'
        assert existing.name == 'Admin edit'
