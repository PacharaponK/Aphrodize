from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter()


@router.get("/health", summary="Liveness check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capabilities", summary="Available optional image workflows")
async def capabilities() -> dict[str, bool]:
    return {
        "annotation_review_available": bool(
            settings.label_studio_api_key and settings.label_studio_project_id > 0
        ),
    }
