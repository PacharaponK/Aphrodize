from types import SimpleNamespace

import pytest

from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import attach_catalog_products, recommendations_for
from tests.test_product_recommendations import catalog_product, safe_profile


def recommendation(pixels, *, eye_pixels=None, evaluated_pixels=10000, **answers):
    regions = {
        "forehead": {
            "score": min(100, pixels / 5),
            "wrinkle_pixels": pixels,
            "evaluated_pixels": evaluated_pixels,
        }
    }
    if eye_pixels is not None:
        regions["image_left_periocular"] = {
            "score": min(100, eye_pixels / 5),
            "wrinkle_pixels": eye_pixels,
            "evaluated_pixels": 10000,
        }
    candidate = SimpleNamespace(
        status=AnalysisStatus.completed,
        image_quality_score=1,
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "v1",
                "confidence": {
                    "calibration_status": "calibrated",
                    "calibration_version": "v1",
                },
            },
            "derived_score": {"score_version": "v1", "roi_version": "v1", "regions": regions},
        },
    )
    return recommendations_for(
        candidate, safe_profile(**{"skin_type": "dry", "age_group": "25_34", **answers})
    )


@pytest.mark.parametrize(
    "pixels,targeted",
    [
        (0, False),
        (100, False),
        (165, False),
        (181, False),
        (182, True),
        (200, True),
        (335, True),
        (1000, True),
    ],
)
def test_area_changes_targeted_categories_with_low_boundary_buffer(pixels, targeted):
    result = recommendation(pixels)
    assert any(i["rule_id"] == "R-WRINKLE-FACE-001" for i in result["recommendations"]) == targeted
    assert any(i["rule_id"] == "R-MOIST-DRY-001" for i in result["recommendations"])


def test_uncapped_area_orders_concerns_and_preserves_safety():
    result = recommendation(500, eye_pixels=1000)
    assert [i["rule_id"] for i in result["recommendations"][:2]] == [
        "R-WRINKLE-EYE-001",
        "R-WRINKLE-FACE-001",
    ]
    assert result["recommendations"][0]["priority_area_ratio"] == 0.1
    assert result["image_context"]["area_policy"] == "owner_reviewed_provisional"
    assert recommendation(1000, age_group="13_17")["recommendations"][0]["rule_id"].startswith(
        "R-YOUTH"
    )
    assert recommendation(1000, skin_sensitivity="high")["recommendations"] == []


def test_skin_type_specific_catalog_matches_precede_all_skin_without_inventing_band_claims():
    result = recommendation(200)
    generic = catalog_product(
        category="treatment",
        target_skin_types=["all"],
        concerns=["wrinkle-care"],
        application_regions=["face"],
    )
    specific = catalog_product(
        category="treatment",
        target_skin_types=["dry"],
        concerns=["wrinkle-care"],
        application_regions=["face"],
    )
    attach_catalog_products(result, [generic, specific])
    item = next(i for i in result["recommendations"] if i["rule_id"] == "R-WRINKLE-FACE-001")
    assert [p["id"] for p in item["products"]] == [str(specific.id), str(generic.id)]
    assert item["products"][0]["matched_claims"] == ["wrinkle-care"]


@pytest.mark.parametrize("pixels,evaluated", [(True, 10000), (10001, 10000), (0, 0)])
def test_malformed_measurements_do_not_trigger_targeted_products(pixels, evaluated):
    result = recommendation(pixels, evaluated_pixels=evaluated)
    assert result["status"] == "ready"
    assert all(not item["rule_id"].startswith("R-WRINKLE") for item in result["recommendations"])
    assert result["image_context"]["area_measurements"] == []
