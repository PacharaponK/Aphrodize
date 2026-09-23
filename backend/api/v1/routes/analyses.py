from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.analysis import AnalysisRead
from backend.core.db.models import Analysis, Questionnaire, User
from backend.core.db.session import get_session
from backend.services.analysis_service import create_analysis, recommendations_for

router = APIRouter()


def serialize(analysis: Analysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        status=analysis.status.value,
        model_family=analysis.model_family,
        model_version=analysis.model_version,
        image_quality_score=analysis.image_quality_score,
        quality_flags=analysis.quality_flags or [],
        result=analysis.result,
        error_category=analysis.error_category,
        created_at=analysis.created_at,
    )


@router.post("/users/{user_id}", response_model=AnalysisRead, status_code=status.HTTP_202_ACCEPTED)
async def submit_analysis(
    user_id: UUID,
    image: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> AnalysisRead:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    analysis = await create_analysis(session, user_id, image)
    return serialize(analysis)


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: UUID, session: AsyncSession = Depends(get_session)
) -> AnalysisRead:
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return serialize(analysis)


@router.get("/{analysis_id}/recommendations")
async def get_recommendations(
    analysis_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict:
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    questionnaire = await session.scalar(
        select(Questionnaire)
        .where(Questionnaire.user_id == analysis.user_id)
        .order_by(Questionnaire.created_at.desc())
        .limit(1)
    )
    return recommendations_for(analysis, questionnaire.answers if questionnaire else {})
