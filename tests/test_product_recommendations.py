from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.core.db.models import AnalysisStatus
from backend.services.analysis_service import attach_catalog_products, recommendations_for


def analysis(*, result=None, quality=1.0, status=AnalysisStatus.completed, user_id=None):
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id or uuid4(),
        status=status,
        image_quality_score=quality,
        result=result,
    )


def safe_profile(**answers):
    return {
        "skin_sensitivity": "low",
        "known_product_allergy": "no",
        "severe_irritation": "no",
        **answers,
    }


def test_self_reported_fallback_is_available_when_wrinkle_gate_is_withheld():
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": False},
            "experimental_score": {"regions": {"image_left_periocular": {"score": 99}}},
        },
    )

    result = recommendations_for(
        candidate,
        safe_profile(
            skin_type="dry",
            outdoor_minutes=90,
            sunscreen_frequency="sometimes",
        ),
    )

    assert result["status"] == "ready"
    assert [item["category"] for item in result["recommendations"]] == [
        "fragrance-free moisturizer",
        "broad-spectrum sunscreen SPF 30+",
    ]
    assert all(item["signal_sources"] == ["self_reported"] for item in result["recommendations"])
    assert result["image_context"] == {
        "status": "withheld",
        "reason": "wrinkle_confidence_not_released",
    }


def test_only_calibrated_released_region_scores_can_be_combined_with_self_report():
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "prediction-v1",
                "confidence": {
                    "calibration_status": "calibrated",
                    "calibration_version": "calibration-v2",
                },
            },
            "derived_score": {
                "score_version": "area-v1",
                "roi_version": "roi-v1",
                "regions": {"image_left_periocular": {"score": 11.5}},
            },
            "experimental_score": {"regions": {"image_left_periocular": {"score": 99.0}}},
        }
    )

    result = recommendations_for(candidate, safe_profile(skin_type="dry"))

    item = result["recommendations"][0]
    assert item["signal_sources"] == ["image", "self_reported"]
    assert item["wrinkle_regions"] == ["image_left_periocular"]
    assert item["wrinkle_region_scores"] == [{"region": "image_left_periocular", "score": 11.5}]
    assert result["image_context"]["score_version"] == "area-v1"
    assert result["image_context"]["regions"]["image_left_periocular"]["score"] == 11.5


def test_image_scores_with_missing_release_versions_are_withheld():
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "prediction-v1",
                "confidence": {"calibration_status": "calibrated", "calibration_version": None},
            },
            "derived_score": {
                "score_version": "area-v1",
                "roi_version": "roi-v1",
                "regions": {"image_left_periocular": {"score": 11.5}},
            },
        }
    )

    result = recommendations_for(candidate, safe_profile(skin_type="dry"))

    assert result["image_context"] == {
        "status": "withheld",
        "reason": "wrinkle_provenance_incomplete",
    }
    assert result["recommendations"][0]["signal_sources"] == ["self_reported"]


@pytest.mark.parametrize(
    "answers",
    [
        {"severe_irritation": True},
        {"known_product_allergy": True},
        {"skin_sensitivity": "high"},
    ],
)
def test_safety_exclusions_block_all_categories(answers):
    result = recommendations_for(analysis(), safe_profile(skin_type="dry", **answers))

    assert result["status"] == "safety_blocked"
    assert result["recommendations"] == []


def test_missing_safety_answers_block_recommendations():
    result = recommendations_for(analysis(), {"skin_type": "dry"})
    assert result["status"] == "safety_blocked"
    assert result["blocked_reason"] == "safety_screening_incomplete"


def test_recent_reported_daily_dryness_can_support_moisturizer_without_using_predictions():
    result = recommendations_for(
        analysis(),
        safe_profile(skin_type="normal"),
        {
            "status": "available",
            "reported_dryness_score_0_10": 7,
            "reported_dryness_date": "2026-09-28",
            # This synthetic prediction must have no effect on recommendation rules.
            "predicted_dryness_score_0_10": 10,
        },
    )

    assert result["recommendations"][0]["category"] == "fragrance-free moisturizer"
    assert result["recommendations"][0]["input_fields"] == ["reported_dryness_score_0_10"]
    assert result["recommendations"][0]["signal_sources"] == ["daily_health_reported"]
    assert result["recommendations"][0]["input_source"] == "daily_health_reported"


def test_image_plus_daily_dryness_preserves_the_actual_daily_trigger():
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "prediction-v1",
                "confidence": {
                    "calibration_status": "calibrated",
                    "calibration_version": "calibration-v2",
                },
            },
            "derived_score": {
                "score_version": "area-v1",
                "roi_version": "roi-v1",
                "regions": {"image_left_periocular": {"score": 11.5}},
            },
        }
    )

    result = recommendations_for(
        candidate,
        safe_profile(skin_type="normal"),
        {
            "status": "available",
            "reported_dryness_score_0_10": 7,
            "reported_dryness_date": "2026-09-28",
        },
    )

    item = result["recommendations"][0]
    assert item["signal_sources"] == ["image", "daily_health_reported"]
    assert item["input_source"] == "image_and_daily_health_reported"
    assert "daily health tracker" in item["rationale"]


def test_recent_daily_outdoor_context_supports_sunscreen_without_claiming_sleep_or_water_effects():
    result = recommendations_for(
        analysis(),
        safe_profile(sunscreen_frequency="sometimes"),
        {
            "status": "no_recent_reported_dryness",
            "lifestyle": {
                "source_table": "daily_health_entries",
                "record_id": str(uuid4()),
                "observed_date": "2026-09-28",
                "outdoor_exposure_choice": 3,
                "sleep_duration_minutes": 300,
                "water_intake_ml": 500,
            },
        },
    )

    item = result["recommendations"][0]
    assert item["category"] == "broad-spectrum sunscreen SPF 30+"
    assert item["signal_sources"] == ["self_reported", "daily_health_reported"]
    assert item["input_source"] == "self_reported_and_daily_health_reported"
    assert item["input_fields"] == ["sunscreen_frequency", "daily_outdoor_exposure_choice"]


def catalog_product(**changes):
    return SimpleNamespace(
        **{
            "id": uuid4(),
            "brand": "Test catalog",
            "name": "Test moisturizer",
            "variant": "",
            "category": "moisturizer",
            "status": "published",
            "reviewed_at": datetime.now(UTC),
            "price_satang": 15900,
            "price_checked_at": None,
            "price_source_url": None,
            "purchase_url": "https://example.com/buy",
            "image_url": "https://example.com/product.jpg",
            "market": "TH",
            "application_regions": [],
            "ingredients_label": "Aqua, Glycerin",
            "ingredients_inci": ["Aqua", "Glycerin"],
            "warnings_label": "Avoid contact with eyes",
            "target_skin_types": ["dry"],
            "concerns": ["fragrance-free"],
            "source_url": "https://example.com/test-product",
            "spf": None,
            "broad_spectrum": False,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "draft"},
        {"status": "archived"},
        {"reviewed_at": None},
        {"ingredients_inci": []},
        {"ingredients_label": ""},
        {"source_url": None},
        {"source_url": "javascript:alert(1)"},
        {"target_skin_types": ["oily"]},
        {"concerns": []},
        {"ingredients_inci": ["Aqua", "Parfum"]},
        {"image_url": None},
        {"purchase_url": None},
        {"purchase_url": "javascript:alert(1)"},
        {"category": "treatment"},
    ],
)
def test_catalog_excludes_unreviewed_incompatible_and_conflicting_labels(changes):
    response = recommendations_for(None, safe_profile(skin_type="dry"))
    attach_catalog_products(response, [catalog_product(**changes)])
    assert response["product_context"]["status"] == "no_match"
    assert response["recommendations"][0]["products"] == []


def test_catalog_preserves_actual_product_data_and_limits_each_category():
    response = recommendations_for(None, safe_profile(skin_type="dry"))
    products = [catalog_product() for _ in range(4)]
    attach_catalog_products(response, products)
    matched = response["recommendations"][0]["products"]
    assert len(matched) == 3
    assert matched[0]["id"] == str(products[0].id)
    assert matched[0]["price_satang"] == 15900
    assert matched[0]["purchase_url"] == products[0].purchase_url
    assert matched[0]["image_url"] == products[0].image_url
    assert matched[0]["warnings_label"] == products[0].warnings_label
    assert matched[0]["matched_claims"] == ["fragrance-free"]
    assert response["product_context"]["status"] == "ready"


def test_reported_allergy_withholds_named_products_even_with_free_text_details():
    response = recommendations_for(
        None,
        safe_profile(
            skin_type="dry",
            known_product_allergy="yes",
            allergy_details="น้ำหอม / Fragrance",
        ),
    )
    attach_catalog_products(response, [catalog_product()])
    assert response["status"] == "ready"  # Category information remains available.
    assert response["product_context"]["status"] == "allergy_review_required"
    assert not response["recommendations"][0].get("products")


def test_sunscreen_requires_spf_and_broad_spectrum_and_sensitivity_label():
    response = recommendations_for(
        None,
        safe_profile(
            skin_type="normal",
            sunscreen_frequency="every_day",
            skin_sensitivity="medium",
        ),
    )
    products = [
        catalog_product(category="sunscreen", target_skin_types=["all"], **changes)
        for changes in (
            {"spf": 15, "broad_spectrum": True},
            {"spf": 50, "broad_spectrum": False},
            {"spf": 50, "broad_spectrum": True, "concerns": []},
            {"spf": 50, "broad_spectrum": True},
        )
    ]
    attach_catalog_products(response, products)
    assert [p["id"] for p in response["recommendations"][0]["products"]] == [str(products[3].id)]


@pytest.mark.parametrize(
    "status",
    [AnalysisStatus.queued, AnalysisStatus.running, AnalysisStatus.failed, AnalysisStatus.rejected],
)
def test_no_product_guidance_before_successful_analysis(status):
    response = recommendations_for(analysis(status=status), safe_profile(skin_type="dry"))
    attach_catalog_products(response, [catalog_product()])
    assert response["recommendations"] == []


def test_released_regions_support_moisturizer_for_other_skin_types_without_treatment_claims():
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "prediction-v1",
                "confidence": {
                    "calibration_status": "calibrated",
                    "calibration_version": "calibration-v2",
                },
            },
            "derived_score": {
                "score_version": "area-v1",
                "roi_version": "roi-v1",
                "regions": {
                    "forehead": {"score": 12},
                    "nasolabial": {"score": 5},
                    "glabella": {"score": float("nan")},
                    "image_left_cheek": {"score": 0},
                    "perioral": {"score": True},
                },
            },
        }
    )
    response = recommendations_for(candidate, safe_profile(skin_type="combination"))
    item = response["recommendations"][0]
    assert item["wrinkle_regions"] == ["forehead", "nasolabial"]
    assert item["signal_sources"] == ["image", "self_reported"]
    assert "do not" in item["rationale"]


@pytest.mark.parametrize("approved", [True, False])
def test_manually_reviewed_release_requires_explicit_approval_provenance(approved):
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "prediction-v1",
                "confidence": {
                    "calibration_status": "not_calibrated",
                    "calibration_version": None,
                    "release_basis": "manual_review",
                    "policy_version": "manual-release-v1",
                    "approval_reference": "owner-review-v1" if approved else None,
                    "passed": True,
                },
            },
            "derived_score": {
                "score_version": "area-v1",
                "roi_version": "roi-v1",
                "regions": {
                    "forehead": {"score": 12},
                },
            },
        }
    )
    response = recommendations_for(candidate, safe_profile(skin_type="normal"))
    if approved:
        assert response["image_context"]["status"] == "eligible"
        assert response["image_context"]["release_basis"] == "manual_review"
        assert response["image_context"]["calibration_version"] is None
        assert response["recommendations"][0]["signal_sources"] == ["image", "self_reported"]
    else:
        assert response["image_context"]["reason"] == "wrinkle_provenance_incomplete"
        assert response["recommendations"][0]["signal_sources"] == ["self_reported"]


@pytest.mark.parametrize("age_group", ["35_44", "13_17", None])
def test_wrinkle_products_require_adult_age_and_the_matching_label_application_area(age_group):
    candidate = analysis(
        result={
            "recommendation_gate": {"eligible": True},
            "model_output": {
                "prediction_version": "v1",
                "confidence": {
                    "calibration_status": "calibrated",
                    "calibration_version": "v1",
                },
            },
            "derived_score": {
                "score_version": "v1",
                "roi_version": "v1",
                "regions": {
                    "forehead": {"score": 12},
                    "image_left_periocular": {"score": 9},
                },
            },
        }
    )
    response = recommendations_for(candidate, safe_profile(skin_type="dry", age_group=age_group))
    eye = catalog_product(
        category="treatment", concerns=["wrinkle-care"], application_regions=["eye_contour"]
    )
    face = catalog_product(
        category="treatment", concerns=["wrinkle-care"], application_regions=["face"]
    )
    unlabeled = catalog_product(category="treatment", concerns=["wrinkle-care"])
    attach_catalog_products(response, [face, eye, unlabeled])
    treatments = [i for i in response["recommendations"] if i["rule_id"].startswith("R-WRINKLE")]
    if age_group == "35_44":
        assert {i["application_region"]: [p["id"] for p in i["products"]] for i in treatments} == {
            "face": [str(face.id)],
            "eye_contour": [str(eye.id)],
        }
    else:
        assert treatments == []
    if age_group == "13_17":
        assert [i["rule_id"] for i in response["recommendations"]] == [
            "R-YOUTH-CLEANSE-001",
            "R-YOUTH-MOIST-001",
            "R-YOUTH-SUN-001",
        ]


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"price_satang": 10001},
        {"price_source_url": None},
        {"price_checked_at": None},
        {"price_checked_at": datetime.now(UTC) - timedelta(days=31)},
        {"price_checked_at": datetime.now(UTC) + timedelta(days=1)},
        {"price_checked_at": datetime.now()},
        {"market": "US"},
    ],
)
def test_thai_budget_filter_requires_affordable_recent_sourced_price(changes):
    response = recommendations_for(None, safe_profile(skin_type="dry"))
    product = catalog_product(
        **{
            "price_satang": 10000,
            "price_source_url": "https://example.com/th-price",
            "price_checked_at": datetime.now(UTC),
            **changes,
        }
    )
    attach_catalog_products(response, [product], market="TH", max_price_satang=10000)
    assert bool(response["recommendations"][0]["products"]) == (not changes)


def test_structured_allergy_history_is_saved_but_still_withholds_named_products():
    from backend.api.schemas.consent import SafetyScreeningUpdate

    payload = SafetyScreeningUpdate(
        **safe_profile(known_product_allergy="yes", allergy_ingredients=["fragrance", "fragrance"]),
        base_revision_id=uuid4(),
    )
    assert payload.safety_answers()["allergy_ingredients"] == ["fragrance"]
    response = recommendations_for(None, {"skin_type": "dry", **payload.safety_answers()})
    attach_catalog_products(response, [catalog_product()])
    assert response["status"] == "ready"
    assert response["allergy_context"]["ingredients"] == ["fragrance"]
    assert response["product_context"]["status"] == "allergy_review_required"
    assert all(not i.get("products") for i in response["recommendations"])
    payload.known_product_allergy = "no"
    assert payload.require_allergy_details().allergy_ingredients == []


def test_daily_outdoor_one_hour_matches_initial_questionnaire_threshold():
    response = recommendations_for(
        None,
        safe_profile(sunscreen_frequency="sometimes"),
        {
            "lifestyle": {"outdoor_exposure_choice": 2},
        },
    )
    assert response["recommendations"][0]["rule_id"] == "R-SUN-OUTDOOR-001"
