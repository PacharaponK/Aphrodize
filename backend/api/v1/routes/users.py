from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.db.models import Analysis, Consent, User
from backend.core.db.session import get_session
from backend.libs.minio_client import analysis_artifact_key, remove_objects

router = APIRouter()


@router.delete("/{user_id}/images", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_images(user_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    analyses = list(
        (await session.scalars(select(Analysis).where(Analysis.user_id == user_id))).all()
    )
    remove_objects([
        key
        for analysis in analyses
        for key in (
            analysis.object_key,
            analysis_artifact_key(user_id, analysis.id, "overlay"),
            analysis_artifact_key(user_id, analysis.id, "mask"),
        )
    ])
    for analysis in analyses:
        await session.delete(analysis)
    await session.execute(
        Consent.__table__.update()
        .where(Consent.user_id == user_id)
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
