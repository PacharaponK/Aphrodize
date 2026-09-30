import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.schemas.product import ProductInput
from backend.api.v1.routes.products import require_publishable
from backend.services import uv_service


def test_uv_snapshot_freshness_and_clouds_do_not_lower_protection(tmp_path, monkeypatch):
    now = datetime(2026, 9, 29, 8, tzinfo=UTC)
    snapshot = tmp_path / "forecast_snapshot.json"
    monkeypatch.setattr(uv_service, "SNAPSHOT", snapshot)
    payload = {
        "generated_at": (now - timedelta(hours=1)).isoformat(),
        "source": "TEMIS clear sky",
        "cities": {
            "bangkok": {
                "data_date": "2026-09-28",
                "model_version": "test",
                "days": [
                    {
                        "date": "2026-09-29",
                        "uv_index_clear_sky": 11.5,
                        "value_kind": "SARIMAX forecast",
                        "weather": {"cloud_cover_percent": 100},
                    },
                    {
                        "date": "2026-09-30",
                        "uv_index_clear_sky": 7.5,
                        "value_kind": "SARIMAX forecast",
                        "weather": None,
                    },
                ],
            }
        },
    }
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    result = uv_service.load_recommendation("bangkok", now)
    assert [day["level"] for day in result["days"]] == ["extreme", "high"]
    assert "SPF 30" in result["advice"]["product_type"]

    payload["generated_at"] = (now - timedelta(hours=9)).isoformat()
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="eight hours"):
        uv_service.load_recommendation("bangkok", now)


def test_sunscreen_needs_verified_label_before_publication():
    with pytest.raises(ValidationError):
        ProductInput(brand="Test", name="Screen", category="sunscreen", spf=101)
    product = SimpleNamespace(
        category="sunscreen",
        price_satang=10000,
        ingredients_label="Water",
        ingredients_inci=["Aqua"],
        target_skin_types=["all"],
        source_url="https://example.com",
        spf=30,
        broad_spectrum=False,
    )
    with pytest.raises(HTTPException):
        require_publishable(product)
    product.broad_spectrum = True
    require_publishable(product)
