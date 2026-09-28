from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import ValidationError

from backend.api import deps
from backend.api.schemas.product import ProductInput
from backend.api.v1.routes.products import require_publishable


def test_product_requires_reviewed_data_before_publication() -> None:
    with pytest.raises(ValidationError):
        ProductInput(brand=" ", name="Cream", category="moisturizer", price_satang=-1)

    draft = SimpleNamespace(
        price_satang=15900, ingredients_label="Water, Glycerin",
        ingredients_inci=[], target_skin_types=["dry"], source_url="https://example.com/product",
    )
    with pytest.raises(HTTPException) as error:
        require_publishable(draft)
    assert error.value.status_code == 422
    draft.ingredients_inci = ["Aqua", "Glycerin"]
    require_publishable(draft)


def test_admin_credentials_are_separate_from_service_credentials(monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "admin_username", "catalog-admin")
    monkeypatch.setattr(deps.settings, "admin_password", "eightpass")
    with pytest.raises(HTTPException) as error:
        deps.require_admin_credentials(HTTPBasicCredentials(username="aphrodize", password="passwd"))
    assert error.value.status_code == 401
    deps.require_admin_credentials(
        HTTPBasicCredentials(username="catalog-admin", password="eightpass")
    )
    monkeypatch.setattr(deps.settings, "admin_password", "shorter")
    with pytest.raises(HTTPException) as error:
        deps.require_admin_credentials(HTTPBasicCredentials(username="catalog-admin", password="shorter"))
    assert error.value.status_code == 503
