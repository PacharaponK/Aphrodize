import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO
from math import isfinite
from uuid import UUID

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.db.models import Analysis, AnalysisStatus, Consent, Product
from backend.libs.minio_client import put_bytes
from backend.libs.redis_client import get_arq_pool
from backend.libs.wrinkle_area import AREA_BAND_VERSION, assess_visible_area

ANALYSIS_CONSENT_VERSION = "1.0"

RECOMMENDATION_RULE_VERSION = "2026-10-02.1"
RECOMMENDATION_KNOWLEDGE_ID = "aphrodize-category-baseline"
RECOMMENDATION_KNOWLEDGE_VERSION = "1.0.0"
KNOWLEDGE_SOURCES = {
    "aad_dry_skin": {
        "id": "aad-dry-skin-tips",
        "title": "Dermatologists' top tips for relieving dry skin",
        "url": "https://www.aad.org/public/everyday-care/skin-care-basics/dry/dermatologists-tips-relieve-dry-skin",
    },
    "aad_sunscreen": {
        "id": "aad-sunscreen-selection",
        "title": "How to select a sunscreen",
        "url": "https://www.aad.org/spot-skin-cancer/learn-about-skin-cancer/prevent-skin-cancer/how-to-select-a-sunscreen",
    },
    "aad_oily_skin": {
        "id": "aad-oily-skin-care",
        "title": "How to control oily skin",
        "url": "https://www.aad.org/public/everyday-care/skin-care-basics/dry/oily-skin",
    },
    "aad_basic_routine": {
        "id": "aad-basic-skin-care-routine",
        "title": "Skin care on a budget",
        "url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/skin-care-budget",
    },
    "aad_moisturizer_by_skin_type": {
        "id": "aad-moisturizer-by-skin-type",
        "title": "How to pick the right moisturizer for your skin",
        "url": "https://www.aad.org/public/everyday-care/skin-care-basics/dry/pick-moisturizer",
    },
    "aad_youth_skin_care": {
        "id": "aad-youth-skin-care",
        "title": "A dermatologist’s guide to skincare from growing up to glowing up",
        "url": "https://www.aad.org/news/dermatologist-guide-skincare",
    },
    "aad_anti_aging": {
        "id": "aad-select-anti-aging-products",
        "title": "How to select anti-aging skin care products",
        "url": "https://www.aad.org/public/everyday-care/skin-care-secrets/anti-aging/selecting-anti-aging-products",
    },
}
RECOMMENDATION_DISCLAIMER = (
    "General skin-care product information based on reported inputs and reviewed labels. "
    "A catalog match is not a guarantee against allergy. It is not a diagnosis, treatment advice, "
    "or evidence that a product will change a wrinkle score. Check the full ingredient "
    "list and stop use if irritation occurs."
)


def _released_wrinkle_context(analysis: Analysis) -> dict[str, object]:
    """Expose only quality-gated, non-experimental, versioned wrinkle scores."""
    result = analysis.result or {}
    gate = result.get("recommendation_gate")
    if analysis.status != AnalysisStatus.completed:
        return {"status": "unavailable", "reason": "analysis_not_complete"}
    if (analysis.image_quality_score or 0) < 0.8:
        return {"status": "withheld", "reason": "image_quality_below_threshold"}
    if not isinstance(gate, dict) or gate.get("eligible") is not True:
        return {"status": "withheld", "reason": "wrinkle_confidence_not_released"}
    score = result.get("derived_score")
    if not isinstance(score, dict) or not isinstance(score.get("regions"), dict):
        return {"status": "withheld", "reason": "released_score_missing"}
    # Release requires calibrated evidence or explicit approval of the exact model lineage.
    model_output = result.get("model_output")
    confidence = model_output.get("confidence") if isinstance(model_output, dict) else None
    if not isinstance(confidence, dict):
        return {"status": "withheld", "reason": "wrinkle_calibration_not_released"}
    manual_release = confidence.get("release_basis") == "manual_review"
    if manual_release:
        if not (
            confidence.get("approval_reference")
            and confidence.get("policy_version")
            and confidence.get("passed") is True
        ):
            return {"status": "withheld", "reason": "wrinkle_provenance_incomplete"}
    elif confidence.get("calibration_status") != "calibrated":
        return {"status": "withheld", "reason": "wrinkle_calibration_not_released"}
    if not model_output.get("prediction_version") or (
        not manual_release and not confidence.get("calibration_version")
    ):
        return {"status": "withheld", "reason": "wrinkle_provenance_incomplete"}
    if not score.get("score_version") or not score.get("roi_version"):
        return {"status": "withheld", "reason": "released_score_missing"}
    return {
        "status": "eligible",
        "overall": score.get("overall"),
        "regions": score["regions"],
        "score_version": score.get("score_version"),
        "roi_version": score.get("roi_version"),
        "model_version": model_output.get("prediction_version"),
        "calibration_version": confidence.get("calibration_version"),
        "release_basis": "manual_review" if manual_release else "calibration",
        "approval_reference": confidence.get("approval_reference"),
    }


def recommendations_for(
    analysis: Analysis | None, answers: dict, daily_context: dict[str, object] | None = None
) -> dict:
    """Build deterministic category recommendations from reported inputs and eligible scores."""
    answers = answers if isinstance(answers, dict) else {}
    daily_context = daily_context if isinstance(daily_context, dict) else {}
    image_context = (
        _released_wrinkle_context(analysis)
        if analysis is not None
        else {"status": "unavailable", "reason": "no_analysis"}
    )

    if analysis is not None and analysis.status != AnalysisStatus.completed:
        return {
            "status": "pending"
            if analysis.status
            in {
                AnalysisStatus.queued,
                AnalysisStatus.running,
            }
            else "no_recommendation",
            "recommendations": [],
            "blocked_reason": "analysis_not_complete",
            "image_context": image_context,
            "daily_context": {},
            "rule_version": RECOMMENDATION_RULE_VERSION,
            "knowledge_base": {
                "id": RECOMMENDATION_KNOWLEDGE_ID,
                "version": RECOMMENDATION_KNOWLEDGE_VERSION,
            },
            "disclaimer": RECOMMENDATION_DISCLAIMER,
        }

    # Safety exclusions take precedence and never infer that missing answers mean "no".
    severe_value = answers.get("severe_irritation")
    severe = (
        severe_value is True
        or severe_value == "yes"
        or answers.get("severe_skin_irritation") is True
    )
    allergy_value = answers.get("known_product_allergy")
    allergy = (
        allergy_value is True
        or allergy_value == "yes"
        or answers.get("allergy_or_irritation") is True
    )
    allergy_details = answers.get("allergy_details")
    allergy_details_present = isinstance(allergy_details, str) and bool(allergy_details.strip())
    allergy_ingredients = answers.get("allergy_ingredients", [])
    allergy_ingredients_present = isinstance(allergy_ingredients, list) and bool(
        allergy_ingredients
    )
    sensitivity = answers.get("skin_sensitivity")
    allergy_unresolved = allergy_value not in {False, "no"} and not (
        allergy and (allergy_details_present or allergy_ingredients_present)
    )
    safety_unknown = (
        severe_value not in {False, "no"}
        or allergy_unresolved
        or sensitivity not in {"low", "medium"}
    )
    if (
        severe
        or (allergy and not (allergy_details_present or allergy_ingredients_present))
        or sensitivity == "high"
        or safety_unknown
    ):
        reason = (
            "reported_severe_irritation"
            if severe
            else "reported_allergy"
            if allergy
            else "reported_high_sensitivity"
            if sensitivity == "high"
            else "safety_screening_incomplete"
        )
        return {
            "status": "safety_blocked",
            "recommendations": [],
            "blocked_reason": reason,
            "image_context": image_context,
            "daily_context": daily_context,
            "rule_version": RECOMMENDATION_RULE_VERSION,
            "knowledge_base": {
                "id": RECOMMENDATION_KNOWLEDGE_ID,
                "version": RECOMMENDATION_KNOWLEDGE_VERSION,
            },
            "disclaimer": RECOMMENDATION_DISCLAIMER,
        }

    items: list[dict[str, object]] = []
    skin_type = answers.get("skin_type")
    age_years = answers.get("age_years")
    age_group = answers.get("age_group")
    sunscreen = answers.get("sunscreen_frequency")
    outdoor_minutes = answers.get("outdoor_minutes")
    reported_dryness_context = daily_context.get("reported_dryness")
    reported_dryness = (
        reported_dryness_context.get("value")
        if isinstance(reported_dryness_context, dict)
        else daily_context.get("reported_dryness_score_0_10")
    )
    lifestyle_context = daily_context.get("lifestyle")
    daily_outdoor = (
        lifestyle_context.get("outdoor_exposure_choice")
        if isinstance(lifestyle_context, dict)
        else daily_context.get("outdoor_exposure_choice")
    )

    def add(
        category: str,
        rule_id: str,
        rationale: str,
        input_fields: list[str],
        sources: list[str],
        knowledge_source: dict[str, str],
    ) -> None:
        items.append(
            {
                "category": category,
                "rule_id": rule_id,
                "rule_version": RECOMMENDATION_RULE_VERSION,
                "rationale": rationale,
                "input_source": {
                    ("self_reported",): "self_reported",
                    ("daily_health_reported",): "daily_health_reported",
                    (
                        "self_reported",
                        "daily_health_reported",
                    ): "self_reported_and_daily_health_reported",
                    ("image", "self_reported"): "image_and_self_reported",
                    ("image", "daily_health_reported"): "image_and_daily_health_reported",
                }[tuple(sources)],
                "input_fields": input_fields,
                "signal_sources": sources,
                "knowledge_source": {
                    "id": RECOMMENDATION_KNOWLEDGE_ID,
                    "version": RECOMMENDATION_KNOWLEDGE_VERSION,
                    "reference": knowledge_source,
                },
            }
        )

    if skin_type == "dry" or (isinstance(reported_dryness, int | float) and reported_dryness >= 6):
        moisturizer_fields = (
            ["skin_type"] if skin_type == "dry" else ["reported_dryness_score_0_10"]
        )
        moisturizer_sources = ["self_reported"] if skin_type == "dry" else ["daily_health_reported"]
        moisturizer_rationale = (
            "You reported dry skin. The American Academy of Dermatology lists "
            "fragrance-free skin care and moisturizer among its general dry-skin "
            "tips."
            if skin_type == "dry"
            else "You recently reported skin dryness in the daily health tracker. The "
            "American Academy of Dermatology lists fragrance-free skin care and "
            "moisturizer among its general dry-skin tips."
        )
        add(
            "fragrance-free moisturizer",
            "R-MOIST-DRY-001",
            moisturizer_rationale,
            moisturizer_fields,
            moisturizer_sources,
            KNOWLEDGE_SOURCES["aad_dry_skin"],
        )

    if skin_type == "oily":
        add(
            "gentle, oil-free non-comedogenic cleanser",
            "R-CLEANSE-OILY-001",
            "You reported oily skin. The American Academy of Dermatology "
            "recommends a mild, gentle face wash and products labelled oil-free "
            "or non-comedogenic for oily skin.",
            ["skin_type"],
            ["self_reported"],
            KNOWLEDGE_SOURCES["aad_oily_skin"],
        )

    if skin_type == "combination":
        add(
            "lightweight moisturizer for combination skin",
            "R-MOIST-COMBINATION-001",
            "You reported combination skin. Consider a lightweight moisturizer "
            "for dry areas and avoid applying it to areas that feel oily.",
            ["skin_type"],
            ["self_reported"],
            KNOWLEDGE_SOURCES["aad_moisturizer_by_skin_type"],
        )

    if skin_type == "unsure":
        add(
            "gentle cleanser",
            "R-CLEANSE-STARTER-001",
            "You are unsure of your skin type, so this starts with a simple "
            "gentle-cleanser category rather than a targeted active product.",
            ["skin_type"],
            ["self_reported"],
            KNOWLEDGE_SOURCES["aad_basic_routine"],
        )

    is_under_18 = (isinstance(age_years, int | float) and age_years < 18) or age_group in {
        "under_13",
        "13_17",
    }
    initial_outdoor_high = isinstance(outdoor_minutes, int | float) and outdoor_minutes >= 60
    daily_outdoor_high = type(daily_outdoor) is int and 2 <= daily_outdoor <= 4
    if sunscreen in {"never", "sometimes"} and (initial_outdoor_high or daily_outdoor_high):
        sunscreen_fields = ["sunscreen_frequency"]
        sunscreen_sources = ["self_reported"]
        if initial_outdoor_high:
            sunscreen_fields.insert(0, "outdoor_minutes")
        if daily_outdoor_high:
            sunscreen_fields.append("daily_outdoor_exposure_choice")
            # Sunscreen frequency is always the questionnaire prerequisite. Daily
            # outdoor exposure adds a second source; it never replaces that source.
            sunscreen_sources = ["self_reported", "daily_health_reported"]
        add(
            "broad-spectrum sunscreen SPF 30+",
            "R-SUN-OUTDOOR-001",
            "You reported infrequent sunscreen use and recent outdoor exposure. "
            "AAD recommends broad-spectrum sunscreen with SPF 30 or higher; this "
            "does not explain wrinkle scores.",
            sunscreen_fields,
            sunscreen_sources,
            KNOWLEDGE_SOURCES["aad_sunscreen"],
        )
    elif sunscreen in {"most_days", "every_day"}:
        add(
            "broad-spectrum sunscreen SPF 30+",
            "R-SUN-ROUTINE-001",
            "You reported regular sunscreen use. Continue choosing "
            "broad-spectrum SPF 30+ sun protection as part of a daily routine.",
            ["sunscreen_frequency"],
            ["self_reported"],
            KNOWLEDGE_SOURCES["aad_basic_routine"],
        )

    if skin_type == "normal":
        add(
            "lightweight daily moisturizer",
            "R-MOIST-NORMAL-001",
            "You reported normal skin. A simple moisturizer is a general routine "
            "option; choose a texture that feels comfortable on your skin.",
            ["skin_type"],
            ["self_reported"],
            KNOWLEDGE_SOURCES["aad_moisturizer_by_skin_type"],
        )

    if is_under_18:
        # A simple youth routine replaces adult guidance and has one catalog rule per step.
        items.clear()
        for category, rule_id in (
            ("gentle cleanser", "R-YOUTH-CLEANSE-001"),
            ("fragrance-free moisturizer", "R-YOUTH-MOIST-001"),
            ("broad-spectrum sunscreen SPF 30+", "R-YOUTH-SUN-001"),
        ):
            add(
                category,
                rule_id,
                "You reported an age under 18. Keep a simple routine of gentle cleansing, "
                "fragrance-free moisturizing and SPF 30+ sun protection. Do not add "
                "anti-aging active products without professional advice.",
                ["age_years" if isinstance(age_years, int | float) else "age_group"],
                ["self_reported"],
                KNOWLEDGE_SOURCES["aad_youth_skin_care"],
            )

    # Released regions supply visual context, never product efficacy or application sites.
    if image_context.get("status") == "eligible":
        regions = image_context.get("regions")
        if isinstance(regions, dict):
            wrinkle_regions = [
                name
                for name in (
                    "forehead",
                    "glabella",
                    "image_left_periocular",
                    "image_right_periocular",
                    "image_left_cheek",
                    "image_right_cheek",
                    "nasolabial",
                    "perioral",
                )
                if isinstance(regions.get(name), dict)
                and type(regions[name].get("score")) in {int, float}
                and isfinite(regions[name]["score"])
                and 0 < regions[name]["score"] <= 100
            ]
            area_measurements = {}
            for name in wrinkle_regions:
                value = regions[name]
                try:
                    measured = assess_visible_area(
                        value.get("wrinkle_pixels"), value.get("evaluated_pixels")
                    )
                except ValueError:
                    continue
                if measured["wrinkle_area_ratio"] is None:
                    continue
                ratio = measured["wrinkle_area_ratio"]
                measured["near_boundary"] = any(
                    abs(ratio - boundary) <= boundary * 0.1
                    for boundary in measured["thresholds"].values()
                )
                area_measurements[name] = {"region": name, **measured}
            image_context["area_band_version"] = AREA_BAND_VERSION
            image_context["area_measurements"] = list(area_measurements.values())
            image_context["area_policy"] = "owner_reviewed_provisional"
            for item in items:
                if not wrinkle_regions or "moisturizer" not in item["category"]:
                    continue
                daily_triggered = item["signal_sources"] == ["daily_health_reported"]
                item["signal_sources"] = (
                    ["image", "daily_health_reported"]
                    if daily_triggered
                    else ["image", "self_reported"]
                )
                item["input_source"] = (
                    "image_and_daily_health_reported"
                    if daily_triggered
                    else "image_and_self_reported"
                )
                item["input_fields"] = [*item["input_fields"], "wrinkle_regions"]
                item["wrinkle_regions"] = wrinkle_regions
                item["wrinkle_region_scores"] = [
                    {"region": name, "score": regions[name]["score"]} for name in wrinkle_regions
                ]
                item["wrinkle_area_measurements"] = list(area_measurements.values())
                item["rationale"] += (
                    " Released wrinkle regions are shown as visual context only. They do not "
                    "identify a cause, predict product effects, or authorize use near the eyes."
                )
            adult_age_known = not is_under_18 and (
                age_group in {"18_24", "25_34", "35_44", "45_54", "55_plus"}
                or (type(age_years) in {int, float} and 18 <= age_years <= 120)
            )
            if adult_age_known:
                eye_regions = {"image_left_periocular", "image_right_periocular"}
                for area, relevant_regions in (
                    ("eye_contour", [name for name in wrinkle_regions if name in eye_regions]),
                    ("face", [name for name in wrinkle_regions if name not in eye_regions]),
                ):
                    # ponytail: single-image provisional bands; validate per-region repeatability
                    # before introducing stronger product or longitudinal decisions.
                    relevant_regions = [
                        name
                        for name in relevant_regions
                        if name in area_measurements
                        and area_measurements[name]["visible_area_band"] in {"medium", "high"}
                        and area_measurements[name]["wrinkle_area_ratio"]
                        >= area_measurements[name]["thresholds"]["low_ratio"] * 1.1
                    ]
                    if not relevant_regions:
                        continue
                    add(
                        "wrinkle care for eye contour"
                        if area == "eye_contour"
                        else "wrinkle care for face",
                        "R-WRINKLE-EYE-001" if area == "eye_contour" else "R-WRINKLE-FACE-001",
                        "The approved image marks these regions. Only products whose reviewed "
                        "labels describe wrinkle care for this application area are matched. "
                        "The image does not predict product benefits. Follow the current label.",
                        ["skin_type", "skin_sensitivity", "age_group", "wrinkle_regions"],
                        ["image", "self_reported"],
                        KNOWLEDGE_SOURCES["aad_anti_aging"],
                    )
                    items[-1].update(
                        {
                            "application_region": area,
                            "wrinkle_regions": relevant_regions,
                            "wrinkle_area_measurements": [
                                area_measurements[name] for name in relevant_regions
                            ],
                            "priority_area_ratio": max(
                                area_measurements[name]["wrinkle_area_ratio"]
                                for name in relevant_regions
                            ),
                            "selection_reason": (
                                "provisional_visible_area_above_low_boundary_buffer"
                            ),
                            "wrinkle_region_scores": [
                                {"region": name, "score": regions[name]["score"]}
                                for name in relevant_regions
                            ],
                        }
                    )
            # Order targeted concerns by uncapped area, then keep the basic routine.
            items.sort(key=lambda item: -item.get("priority_area_ratio", 0))

    return {
        "status": "ready" if items else "no_recommendation",
        "recommendations": items,
        "blocked_reason": None if items else "no_supported_rule_inputs",
        "image_context": image_context,
        # This contains user-reported daily signals only.  Synthetic model predictions
        # are intentionally never returned to or consumed by recommendation rules.
        "daily_context": daily_context,
        "allergy_context": {
            "reported": allergy,
            "details": allergy_details.strip() if allergy_details_present else None,
            "ingredients": allergy_ingredients if allergy_ingredients_present else [],
        },
        "profile_context": {
            "skin_type": skin_type,
            "skin_sensitivity": sensitivity,
            "age_years": age_years if isinstance(age_years, int | float) else None,
            "age_group": age_group if isinstance(age_group, str) else None,
            "sex": answers.get("sex") if isinstance(answers.get("sex"), str) else None,
            "sex_note": "Sex is recorded for the profile but does not by itself select a "
            "skincare product category.",
        },
        "rule_version": RECOMMENDATION_RULE_VERSION,
        "knowledge_base": {
            "id": RECOMMENDATION_KNOWLEDGE_ID,
            "version": RECOMMENDATION_KNOWLEDGE_VERSION,
        },
        "disclaimer": RECOMMENDATION_DISCLAIMER,
    }


PRODUCT_RULES = {
    "R-MOIST-DRY-001": ("moisturizer", {"fragrance-free"}),
    "R-CLEANSE-OILY-001": ("cleanser", {"gentle", "oil-free", "non-comedogenic"}),
    "R-MOIST-COMBINATION-001": ("moisturizer", {"lightweight"}),
    "R-CLEANSE-STARTER-001": ("cleanser", {"gentle"}),
    "R-MOIST-NORMAL-001": ("moisturizer", {"lightweight"}),
    "R-SUN-OUTDOOR-001": ("sunscreen", set()),
    "R-SUN-ROUTINE-001": ("sunscreen", set()),
    "R-YOUTH-CLEANSE-001": ("cleanser", {"gentle"}),
    "R-YOUTH-MOIST-001": ("moisturizer", {"fragrance-free"}),
    "R-YOUTH-SUN-001": ("sunscreen", set()),
    "R-WRINKLE-EYE-001": ("treatment", {"wrinkle-care"}),
    "R-WRINKLE-FACE-001": ("treatment", {"wrinkle-care"}),
}


def attach_catalog_products(
    response: dict,
    products: list[Product],
    *,
    market: str | None = None,
    max_price_satang: int | None = None,
) -> None:
    """Match reviewed label claims, never infer allergy safety from free text."""
    if response["status"] != "ready":
        response["product_context"] = {"status": response["status"]}
        return
    if response.get("allergy_context", {}).get("reported"):
        # ponytail: free-text allergies cannot resolve INCI aliases or cross-reactivity;
        # add clinician-reviewed structured exclusions before selecting named products.
        response["product_context"] = {"status": "allergy_review_required"}
        return

    profile = response.get("profile_context", {})
    skin_type = profile.get("skin_type")
    matched = False
    now = datetime.now(UTC)
    products = sorted(products, key=lambda product: getattr(product, "market", None) != "TH")
    for item in response["recommendations"]:
        item["products"] = []
        rule = PRODUCT_RULES.get(item["rule_id"])
        if rule is None:
            continue
        category, required_claims = rule
        for product in sorted(
            products,
            key=lambda product: skin_type not in (product.target_skin_types or []),
        ):
            if product.status != "published" or product.reviewed_at is None:
                continue
            # Named recommendations must include reviewed shopping links and real photos.
            if not all(
                isinstance(url, str) and url.startswith("https://")
                for url in (
                    getattr(product, "purchase_url", None),
                    getattr(product, "image_url", None),
                )
            ):
                continue
            if market is not None and getattr(product, "market", None) != market:
                continue
            if max_price_satang is not None:
                checked = product.price_checked_at
                if not (
                    product.price_satang is not None
                    and product.price_satang <= max_price_satang
                    and getattr(product, "price_source_url", None)
                    and checked is not None
                    and checked.tzinfo is not None
                    and now - timedelta(days=30) <= checked <= now
                ):
                    continue
            if not all(
                (
                    product.ingredients_label,
                    product.ingredients_inci,
                    product.target_skin_types,
                    product.source_url,
                )
            ):
                continue
            if not product.source_url.startswith(("https://", "http://")):
                continue
            if product.category != category or not (
                skin_type in product.target_skin_types or "all" in product.target_skin_types
            ):
                continue
            area = item.get("application_region")
            if area and area not in (getattr(product, "application_regions", None) or []):
                continue
            # Claims are entered by the catalog reviewer from the product's label/source.
            claims = {value.strip().casefold() for value in product.concerns}
            required = required_claims | (
                {"fragrance-free"} if profile.get("skin_sensitivity") == "medium" else set()
            )
            if not required.issubset(claims):
                continue
            if "fragrance-free" in required and any(
                token in ingredient.casefold()
                for ingredient in product.ingredients_inci
                for token in ("parfum", "fragrance", "perfume")
            ):
                continue
            if category == "sunscreen" and not (
                product.broad_spectrum and product.spf is not None and product.spf >= 30
            ):
                continue
            item["products"].append(
                {
                    "id": str(product.id),
                    "brand": product.brand,
                    "name": product.name,
                    "variant": product.variant,
                    "price_satang": product.price_satang,
                    "price_checked_at": product.price_checked_at,
                    "ingredients_inci": product.ingredients_inci,
                    "warnings_label": product.warnings_label,
                    "source_url": product.source_url,
                    "reviewed_at": product.reviewed_at,
                    "market": getattr(product, "market", None),
                    "price_source_url": getattr(product, "price_source_url", None),
                    "purchase_url": getattr(product, "purchase_url", None),
                    "image_url": getattr(product, "image_url", None),
                    "application_regions": getattr(product, "application_regions", None) or [],
                    "matched_skin_type": skin_type
                    if skin_type in product.target_skin_types
                    else "all",
                    "matched_claims": sorted(required),
                    "match_reason": "reviewed_label_and_skin_type",
                }
            )
            matched = True
            if len(item["products"]) == 3:
                break
    response["product_context"] = {
        "status": "ready" if matched else "no_match",
        "market": market,
        "max_price_satang": max_price_satang,
        "price_max_age_days": 30,
    }


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def image_quality_flags(payload: bytes) -> tuple[float, list[str]]:
    """A conservative preflight gate; a trained quality model replaces it in production."""
    try:
        # Decode just enough to learn the dimensions and verify the image container.
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError):
        # A malformed file is rejected before any bytes reach MinIO.
        return 0.0, ["unreadable_image"]
    flags = []
    # The AI pipeline needs both dimensions to be at least 512 pixels.
    if min(width, height) < 512:
        flags.append("resolution_too_low")
    return (0.0 if flags else 1.0), flags


async def create_analysis(session: AsyncSession, user_id: UUID, image: UploadFile) -> Analysis:
    # Only the image-analysis consent authorizes an original image upload.
    active_consent = await session.scalar(
        select(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.version == ANALYSIS_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        )
        .limit(1)
    )
    if active_consent is None:
        raise HTTPException(
            status_code=403, detail="Active consent is required before image upload"
        )
    # Check the declared media type before reading at most one byte past the limit.
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are accepted")
    payload = await image.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds upload limit")
    # Reject unreadable or undersized images before storing bytes or queuing inference.
    quality_score, quality_flags = image_quality_flags(payload)
    # Reserve a unique private key; rejected uploads never write to this key.
    object_key = f"users/{user_id}/original/{uuid.uuid4()}"
    if not quality_flags:
        put_bytes(object_key, payload, image.content_type)
    # Record either a terminal preflight rejection or a queued analysis.
    analysis = Analysis(
        user_id=user_id,
        object_key=object_key,
        content_type=image.content_type,
        image_quality_score=quality_score,
        quality_flags=quality_flags,
        model_family="image_segmentation",
        model_version=settings.model_version,
        status=AnalysisStatus.rejected if quality_flags else AnalysisStatus.queued,
        error_category="image_quality" if quality_flags else None,
    )
    session.add(analysis)
    # Commit before queuing so the worker can immediately fetch this row by ID.
    await session.commit()
    await session.refresh(analysis)
    if not quality_flags:
        # Queue only the ID; the worker reads the image directly from MinIO.
        redis = await get_arq_pool()
        await redis.enqueue_job("run_inference", str(analysis.id), _queue_name="inference")
        await redis.close()
    return analysis
