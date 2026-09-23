"""FastAPI adapter for privacy-preserving one-image wrinkle analysis."""

from __future__ import annotations

import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from PIL import UnidentifiedImageError

from ai.ffhq_wrinkle.quality import QualityGateError

from .schemas import AnalysisResponse, QualityRejection
from .service import WrinkleAnalysisService

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def create_app(service: WrinkleAnalysisService | None = None) -> FastAPI:
    app = FastAPI(title="Aphrodize Wrinkle Analysis API", version="1.0.0")
    policy_bundle = os.environ.get("APHRODIZE_WRINKLE_POLICY_BUNDLE")
    analysis_service = service or WrinkleAnalysisService(released_policy_bundle=policy_bundle)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/wrinkle/analyze",
        response_model=AnalysisResponse,
        responses={422: {"model": QualityRejection}},
    )
    async def analyze(
        image: UploadFile = File(...),
        consent_accepted: bool = Form(...),
    ) -> AnalysisResponse | JSONResponse:
        if not consent_accepted:
            raise HTTPException(status_code=403, detail="explicit consent is required")
        if image.content_type not in ALLOWED_MEDIA_TYPES:
            raise HTTPException(status_code=415, detail="expected a JPEG, PNG, or WebP image")
        data = await image.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="image exceeds the 10 MiB upload limit")
        if not data:
            raise HTTPException(status_code=400, detail="image is empty")
        try:
            return await run_in_threadpool(
                analysis_service.analyze_bytes,
                data,
                ALLOWED_MEDIA_TYPES[image.content_type],
            )
        except QualityGateError as error:
            detail = QualityRejection(quality_flags=list(error.assessment.issues)).model_dump()
            return JSONResponse(status_code=422, content=detail)
        except UnidentifiedImageError as error:
            raise HTTPException(
                status_code=400, detail="image content could not be decoded"
            ) from error

    return app


app = create_app()
