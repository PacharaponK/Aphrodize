from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml
from fastapi import HTTPException
from pydantic import ValidationError

from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import attach_catalog_products, recommendations_for
from backend.services.fixture_service import load_products, products_from_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "backend" / "fixtures" / "products.yaml"


class CatalogSession:
    def __init__(self):
        self.products = {}
        self.commits = 0

    async def scalar(self, query):
        source_url = query.compile().params["source_url_1"]
        product = self.products.get(source_url)
        return product

    def add(self, product):
        product.id = uuid4()
        self.products[product.source_url] = product

    async def commit(self):
        self.commits += 1


async def test_product_import_is_repeatable_and_keeps_admin_edits():
    session = CatalogSession()
    assert await load_products(FIXTURE, session) == len(products_from_fixture(FIXTURE))
    existing = next(iter(session.products.values()))
    existing.status = "archived"
    existing.name = "Edited by admin"
    assert await load_products(FIXTURE, session) == 0
    assert session.commits == 1
    assert existing.status == "archived"
    assert existing.name == "Edited by admin"
    assert all(product.reviewed_at.year == 2026 for product in session.products.values())
    assert all(
        product.price_source_url
        for product in session.products.values()
        if product.price_satang is not None
    )
    assert any(
        product.market == "TH" and product.price_satang is not None
        for product in session.products.values()
    )
    vanicream = next(p for p in session.products.values() if p.brand == "Vanicream")
    assert "1,2-hexanediol" in vanicream.ingredients_inci


@pytest.mark.parametrize("invalid", ["missing_ingredients", "duplicate", "naive_review_date"])
async def test_invalid_product_batch_does_not_write_any_rows(tmp_path, invalid):
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    if invalid == "missing_ingredients":
        data["products"][-1]["ingredients_inci"] = []
    elif invalid == "duplicate":
        data["products"].append(data["products"][0])
    else:
        data["reviewed_at"] = "2026-10-01T00:00:00"
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    session = CatalogSession()
    with pytest.raises((ValueError, ValidationError, HTTPException)):
        await load_products(path, session)
    assert session.products == {}
    assert session.commits == 0


@pytest.mark.parametrize("skin_type", ["dry", "normal", "combination", "oily", "unsure"])
@pytest.mark.parametrize("sensitivity", ["low", "medium"])
def test_real_fixture_matches_each_supported_profile(skin_type, sensitivity):
    profile = {
        "skin_type": skin_type,
        "skin_sensitivity": sensitivity,
        "known_product_allergy": "no",
        "severe_irritation": "no",
        "sunscreen_frequency": "never",
    }
    analysis = SimpleNamespace(
        id=uuid4(),
        status=AnalysisStatus.completed,
        result=None,
        image_quality_score=1,
    )
    response = recommendations_for(analysis, profile)
    attach_catalog_products(response, products_from_fixture(FIXTURE))
    assert response["status"] == "ready"
    assert response["recommendations"]
    assert all(item["products"] for item in response["recommendations"])
    if skin_type in {"dry", "normal", "combination"}:
        moisturizer = next(i for i in response["recommendations"] if "moisturizer" in i["category"])
        assert len(moisturizer["products"]) >= 2


def test_real_fixture_does_not_bypass_reported_allergy():
    analysis = SimpleNamespace(
        id=uuid4(),
        status=AnalysisStatus.completed,
        result=None,
        image_quality_score=1,
    )
    response = recommendations_for(
        analysis,
        {
            "skin_type": "dry",
            "skin_sensitivity": "low",
            "severe_irritation": "no",
            "known_product_allergy": "yes",
            "allergy_details": "niacinamide",
        },
    )
    attach_catalog_products(response, products_from_fixture(FIXTURE))
    assert response["product_context"]["status"] == "allergy_review_required"
    assert all(not item.get("products") for item in response["recommendations"])
