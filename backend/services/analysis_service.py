import uuid
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.db.models import Analysis, AnalysisStatus, Consent
from backend.libs.minio_client import put_bytes
from backend.libs.redis_client import get_arq_pool

ANALYSIS_CONSENT_VERSION = "1.0"

RECOMMENDATION_RULE_VERSION = "2026-09-28.1"
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
}
RECOMMENDATION_DISCLAIMER = (
    "General product-category information only. It is not a diagnosis, treatment advice, "
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
    # Scores in this app are experimental until explicitly released by a calibrated policy.
    model_output = result.get("model_output")
    confidence = model_output.get("confidence") if isinstance(model_output, dict) else None
    if not isinstance(confidence, dict) or confidence.get("calibration_status") != "calibrated":
        return {"status": "withheld", "reason": "wrinkle_calibration_not_released"}
    if not confidence.get("calibration_version") or not model_output.get("prediction_version"):
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

    # Safety exclusions take precedence and never infer that missing answers mean "no".
    severe_value = answers.get("severe_irritation")
    severe = severe_value is True or severe_value == "yes" or answers.get("severe_skin_irritation") is True
    allergy_value = answers.get("known_product_allergy")
    allergy = allergy_value is True or allergy_value == "yes" or answers.get("allergy_or_irritation") is True
    allergy_details = answers.get("allergy_details")
    allergy_details_present = isinstance(allergy_details, str) and bool(allergy_details.strip())
    sensitivity = answers.get("skin_sensitivity")
    allergy_unresolved = allergy_value not in {False, "no"} and not (allergy and allergy_details_present)
    safety_unknown = severe_value not in {False, "no"} or allergy_unresolved or sensitivity not in {"low", "medium"}
    if severe or (allergy and not allergy_details_present) or sensitivity == "high" or safety_unknown:
        reason = "reported_severe_irritation" if severe else "reported_allergy" if allergy else "reported_high_sensitivity" if sensitivity == "high" else "safety_screening_incomplete"
        return {
            "status": "safety_blocked",
            "recommendations": [],
            "blocked_reason": reason,
            "image_context": image_context,
            "daily_context": daily_context,
            "rule_version": RECOMMENDATION_RULE_VERSION,
            "knowledge_base": {"id": RECOMMENDATION_KNOWLEDGE_ID, "version": RECOMMENDATION_KNOWLEDGE_VERSION},
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

    def add(category: str, rule_id: str, rationale: str, input_fields: list[str], sources: list[str], knowledge_source: dict[str, str]) -> None:
        items.append({
            "category": category,
            "rule_id": rule_id,
            "rule_version": RECOMMENDATION_RULE_VERSION,
            "rationale": rationale,
            "input_source": {
                ("self_reported",): "self_reported",
                ("daily_health_reported",): "daily_health_reported",
                ("self_reported", "daily_health_reported"): "self_reported_and_daily_health_reported",
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
        })

    if skin_type == "dry" or (
        isinstance(reported_dryness, (int, float)) and reported_dryness >= 6
    ):
        moisturizer_fields = ["skin_type"] if skin_type == "dry" else ["reported_dryness_score_0_10"]
        moisturizer_sources = ["self_reported"] if skin_type == "dry" else ["daily_health_reported"]
        moisturizer_rationale = (
            "You reported dry skin. The American Academy of Dermatology lists fragrance-free skin care and moisturizer among its general dry-skin tips."
            if skin_type == "dry"
            else "You recently reported skin dryness in the daily health tracker. The American Academy of Dermatology lists fragrance-free skin care and moisturizer among its general dry-skin tips."
        )
        add(
            "fragrance-free moisturizer", "R-MOIST-DRY-001",
            moisturizer_rationale, moisturizer_fields, moisturizer_sources, KNOWLEDGE_SOURCES["aad_dry_skin"],
        )

    if skin_type == "oily":
        add(
            "gentle, oil-free non-comedogenic cleanser", "R-CLEANSE-OILY-001",
            "You reported oily skin. The American Academy of Dermatology recommends a mild, gentle face wash and products labelled oil-free or non-comedogenic for oily skin.",
            ["skin_type"], ["self_reported"], KNOWLEDGE_SOURCES["aad_oily_skin"],
        )

    if skin_type == "combination":
        add(
            "lightweight moisturizer for combination skin", "R-MOIST-COMBINATION-001",
            "You reported combination skin. Consider a lightweight moisturizer for dry areas and avoid applying it to areas that feel oily.",
            ["skin_type"], ["self_reported"], KNOWLEDGE_SOURCES["aad_moisturizer_by_skin_type"],
        )

    if skin_type == "unsure":
        add(
            "gentle cleanser", "R-CLEANSE-STARTER-001",
            "You are unsure of your skin type, so this starts with a simple gentle-cleanser category rather than a targeted active product.",
            ["skin_type"], ["self_reported"], KNOWLEDGE_SOURCES["aad_basic_routine"],
        )

    is_under_18 = (
        isinstance(age_years, (int, float)) and age_years < 18
    ) or age_group in {"under_13", "13_17"}
    if is_under_18:
        add(
            "simple gentle youth skin-care routine", "R-YOUTH-BASIC-001",
            "You reported an age under 18. Keep the routine simple: gentle cleansing, a fragrance-free moisturizer, and broad-spectrum SPF 30+ sun protection; avoid adding anti-aging active products without professional advice.",
            ["age_years" if isinstance(age_years, (int, float)) else "age_group"], ["self_reported"], KNOWLEDGE_SOURCES["aad_youth_skin_care"],
        )

    initial_outdoor_high = isinstance(outdoor_minutes, (int, float)) and outdoor_minutes >= 60
    daily_outdoor_high = isinstance(daily_outdoor, int) and daily_outdoor >= 3
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
            "broad-spectrum sunscreen SPF 30+", "R-SUN-OUTDOOR-001",
            "You reported infrequent sunscreen use and recent outdoor exposure. AAD recommends broad-spectrum sunscreen with SPF 30 or higher; this does not explain wrinkle scores.",
            sunscreen_fields, sunscreen_sources, KNOWLEDGE_SOURCES["aad_sunscreen"],
        )
    elif sunscreen in {"most_days", "every_day"}:
        add(
            "broad-spectrum sunscreen SPF 30+", "R-SUN-ROUTINE-001",
            "You reported regular sunscreen use. Continue choosing broad-spectrum SPF 30+ sun protection as part of a daily routine.",
            ["sunscreen_frequency"], ["self_reported"], KNOWLEDGE_SOURCES["aad_basic_routine"],
        )

    if skin_type == "normal":
        add(
            "lightweight daily moisturizer", "R-MOIST-NORMAL-001",
            "You reported normal skin. A simple moisturizer is a general routine option; choose a texture that feels comfortable on your skin.",
            ["skin_type"], ["self_reported"], KNOWLEDGE_SOURCES["aad_moisturizer_by_skin_type"],
        )

    # Eligible image context can support a moisturizer suggestion only alongside a user-reported factor.
    # Experimental scores are never read here.
    if image_context.get("status") == "eligible" and items and items[0]["category"] == "fragrance-free moisturizer":
        regions = image_context.get("regions")
        if isinstance(regions, dict):
            wrinkle_regions = [
                name for name in ("image_left_periocular", "image_right_periocular")
                if isinstance(regions.get(name), dict)
                and isinstance(regions[name].get("score"), (int, float))
            ]
            if wrinkle_regions:
                daily_triggered = items[0]["signal_sources"] == ["daily_health_reported"]
                items[0]["signal_sources"] = ["image", "daily_health_reported"] if daily_triggered else ["image", "self_reported"]
                items[0]["input_source"] = "image_and_daily_health_reported" if daily_triggered else "image_and_self_reported"
                items[0]["input_fields"] = [*items[0]["input_fields"], "wrinkle_regions"]
                items[0]["wrinkle_regions"] = wrinkle_regions
                items[0]["wrinkle_region_scores"] = [
                    {"region": name, "score": regions[name]["score"]}
                    for name in wrinkle_regions
                ]
                items[0]["rationale"] = (
                    "The released wrinkle score includes periocular regions, and you recently reported skin dryness in the daily health tracker. AAD lists fragrance-free moisturizer among its general dry-skin tips. The score is a visual measurement only; this does not identify a cause or predict product effects."
                    if daily_triggered
                    else "The released wrinkle score includes periocular regions, and you reported dry skin. AAD lists fragrance-free moisturizer among its general dry-skin tips. The score is a visual measurement only; this does not identify a cause or predict product effects."
                )

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
        },
        "profile_context": {
            "age_years": age_years if isinstance(age_years, (int, float)) else None,
            "age_group": age_group if isinstance(age_group, str) else None,
            "sex": answers.get("sex") if isinstance(answers.get("sex"), str) else None,
            "sex_note": "Sex is recorded for the profile but does not by itself select a skincare product category.",
        },
        "rule_version": RECOMMENDATION_RULE_VERSION,
        "knowledge_base": {"id": RECOMMENDATION_KNOWLEDGE_ID, "version": RECOMMENDATION_KNOWLEDGE_VERSION},
        "disclaimer": RECOMMENDATION_DISCLAIMER,
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
        select(Consent).where(
            Consent.user_id == user_id,
            Consent.version == ANALYSIS_CONSENT_VERSION,
            Consent.revoked_at.is_(None),
        ).limit(1)
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
