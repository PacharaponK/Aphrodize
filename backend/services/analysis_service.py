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

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def image_quality_flags(payload: bytes) -> tuple[float, list[str]]:
    """A conservative preflight gate; a trained quality model replaces it in production."""
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError):
        return 0.0, ["unreadable_image"]
    flags = []
    if min(width, height) < 512:
        flags.append("resolution_too_low")
    return (0.0 if flags else 1.0), flags


async def create_analysis(session: AsyncSession, user_id: UUID, image: UploadFile) -> Analysis:
    active_consent = await session.scalar(
        select(Consent).where(Consent.user_id == user_id, Consent.revoked_at.is_(None)).limit(1)
    )
    if active_consent is None:
        raise HTTPException(
            status_code=403, detail="Active consent is required before image upload"
        )
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are accepted")
    payload = await image.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds upload limit")
    quality_score, quality_flags = image_quality_flags(payload)
    object_key = f"users/{user_id}/original/{uuid.uuid4()}"
    if not quality_flags:
        put_bytes(object_key, payload, image.content_type)
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
    await session.commit()
    await session.refresh(analysis)
    if not quality_flags:
        redis = await get_arq_pool()
        await redis.enqueue_job("run_inference", str(analysis.id), _queue_name="inference")
        await redis.close()
    return analysis


def recommendations_for(analysis: Analysis, answers: dict) -> dict:
    if analysis.status != AnalysisStatus.completed:
        return {"recommendations": [], "blocked_reason": "Analysis is not complete."}
    if analysis.image_quality_score is None or analysis.image_quality_score < 0.8:
        return {"recommendations": [], "blocked_reason": "Image quality is insufficient."}
    gate = (analysis.result or {}).get("recommendation_gate", {})
    if not gate.get("eligible", False):
        return {"recommendations": [], "blocked_reason": "AI confidence gate did not pass."}
    if answers.get("severe_irritation") or answers.get("retinoid_contraindication"):
        return {"recommendations": [], "blocked_reason": "Safety rule blocked a recommendation."}
    return {
        "recommendations": [
            {
                "category": "broad-spectrum sunscreen",
                "rationale": "General skincare guidance; not a treatment claim.",
                "source": "Reviewed guidance required before production release.",
                "rule_version": "1.0.0",
            }
        ],
        "blocked_reason": None,
    }
