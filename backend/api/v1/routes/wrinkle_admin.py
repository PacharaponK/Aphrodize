"""Authenticated operator controls; model work always runs on the training queue."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from backend.api.deps import require_model_reviewer
from backend.core.consents import WRINKLE_TRAINING_CONSENT_VERSION
from backend.core.db.models import AnnotationTask, Consent, TrainingRun
from backend.core.db.session import get_session
from backend.core.observability import enqueue_job
from backend.libs.redis_client import get_arq_pool
from backend.services import wrinkle_lifecycle as lifecycle
from backend.services.curated_training import APPROVED_DATA_ROOT, sha256_file

router = APIRouter(dependencies=[Depends(require_model_reviewer)])


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: UUID
    annotation_id: int = Field(gt=0, strict=True)
    split: Literal["train", "validation", "test"]


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["retrain", "promote", "rollback", "export"]
    dataset_uri: str | None = Field(default=None, max_length=512)
    epochs: int = Field(default=1, ge=1, le=20, strict=True)
    version: UUID | Literal["initial"] | None = None
    expected_active: UUID | Literal["initial"] | None = None
    selections: list[Selection] = Field(default_factory=list, max_length=100)
    reviewed: bool = False


def list_datasets():
    result = []
    for manifest in APPROVED_DATA_ROOT.glob("*/manifest.json"):
        if not manifest.resolve().is_relative_to(APPROVED_DATA_ROOT.resolve()):
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not data.get("approved_for_training"):
                continue
            result.append(
                {
                    "uri": f"approved://{manifest.parent.name}@{sha256_file(manifest)}",
                    "name": manifest.parent.name,
                    "source": data.get("source"),
                    "counts": {
                        s: sum(x.get("split") == s for x in data.get("samples", []))
                        for s in ("train", "validation", "test")
                    },
                    "subjects": len({x.get("subject_id") for x in data.get("samples", [])}),
                    "expires_at": data.get("expires_at"),
                }
            )
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return result


@router.get("")
async def overview(response: Response, session=Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    row = await lifecycle.deployment(session)
    runs = (
        await session.scalars(
            select(TrainingRun)
            .where(
                TrainingRun.model_family.in_(["image_segmentation", "wrinkle_dataset"]),
            )
            .order_by(TrainingRun.created_at.desc())
            .limit(30)
        )
    ).all()
    tasks = (
        await session.scalars(
            select(AnnotationTask)
            .join(
                Consent,
                Consent.user_id == AnnotationTask.user_id,
            )
            .where(
                Consent.version == WRINKLE_TRAINING_CONSENT_VERSION,
                Consent.revoked_at.is_(None),
                AnnotationTask.expires_at > datetime.now(UTC),
                AnnotationTask.label_studio_task_id.is_not(None),
            )
            .limit(100)
        )
    ).all()
    state = row.state
    from backend.services.wrinkle_datasets import subject_split

    await session.commit()
    return {
        **state,
        "datasets": await asyncio.to_thread(list_datasets),
        "runs": [lifecycle.run_summary(run) for run in runs],
        "review_tasks": [
            {
                "id": str(t.id),
                "label_studio_task_id": t.label_studio_task_id,
                "split": subject_split(t.user_id),
                "expires_at": t.expires_at,
            }
            for t in tasks
        ],
        "score_mode": "experimental; a new checkpoint requires its own calibrated policy",
    }


@router.post("", status_code=202)
async def action(
    payload: Action,
    response: Response,
    session=Depends(get_session),
    actor: str = Depends(require_model_reviewer),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        if payload.action == "retrain":
            if not payload.dataset_uri or payload.expected_active is None:
                raise HTTPException(422, "Choose a dataset and refresh the active version")
            run = await lifecycle.submit(
                session, payload.dataset_uri, payload.epochs, str(payload.expected_active), actor
            )
            return lifecycle.run_summary(run)
        if payload.action in {"promote", "rollback"}:
            if payload.version is None or payload.expected_active is None:
                raise HTTPException(422, "Choose a version and refresh the active version")
            await lifecycle.request_activation(
                session, str(payload.version), str(payload.expected_active), actor, payload.action
            )
            return {"status": "queued"}
        if (
            not payload.reviewed
            or not payload.selections
            or {s.split for s in payload.selections} != {"train", "validation", "test"}
            or len({s.task_id for s in payload.selections}) != len(payload.selections)
        ):
            raise HTTPException(422, "Approve reviewed masks and choose all three distinct splits")
        await lifecycle.deployment(session, lock=True)
        busy = await session.scalar(
            select(TrainingRun.id).where(
                TrainingRun.model_family == "wrinkle_dataset",
                TrainingRun.status.in_(["queued", "running"]),
            )
        )
        if busy:
            raise HTTPException(409, "Dataset export is already in progress")
        run = TrainingRun(
            model_family="wrinkle_dataset",
            dataset_uri="pending",
            config={
                "actor": actor,
                "requested_at": lifecycle.now(),
                "selections": [s.model_dump(mode="json") for s in payload.selections],
            },
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        redis = None
        try:
            redis = await get_arq_pool()
            if (
                await enqueue_job(redis, "run_training", str(run.id), _queue_name="training")
                is None
            ):
                raise RuntimeError("Queue rejected export")
        except Exception as error:
            run.status = "failed"
            run.config = {**run.config, "error": "Export queue unavailable; retry"}
            await session.commit()
            raise HTTPException(503, "Export queue unavailable; retry") from error
        finally:
            if redis:
                await redis.close()
        return lifecycle.run_summary(run)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise HTTPException(
            409, "Dataset/model unavailable, expired or changed; refresh"
        ) from error
