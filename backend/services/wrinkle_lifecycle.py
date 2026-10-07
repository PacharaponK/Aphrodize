"""Admin wrinkle training and deployment, using the existing queue and model loader."""

import asyncio
import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.core.db.models import TrainingRun, WrinkleDeployment
from backend.core.observability import enqueue_job
from backend.libs.redis_client import get_arq_pool
from backend.services.curated_training import (
    APPROVED_DATA_ROOT,
    dataset_path,
    validate_manifest,
)

INITIAL = "initial"
MODEL_ROOT = APPROVED_DATA_ROOT.parents[1] / "models/ffhq-wrinkle"


def now() -> str:
    return datetime.now(UTC).isoformat()


async def deployment(session, *, lock=False) -> WrinkleDeployment:
    # ON CONFLICT avoids a startup race between several worker processes.
    if session.bind.dialect.name == "postgresql":
        await session.execute(
            insert(WrinkleDeployment)
            .values(
                id="wrinkle",
                state={"active": INITIAL, "history": [], "pending": None},
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
    row = await session.scalar(
        select(WrinkleDeployment)
        .where(
            WrinkleDeployment.id == "wrinkle",
        )
        .with_for_update()
        if lock
        else select(WrinkleDeployment).where(
            WrinkleDeployment.id == "wrinkle",
        )
    )
    if row is None:
        row = WrinkleDeployment(
            id="wrinkle",
            state={
                "active": INITIAL,
                "history": [],
                "pending": None,
            },
        )
        session.add(row)
        await session.flush()
    return row


def initial_manifest() -> str | None:
    return os.environ.get("APHRODIZE_WRINKLE_APPROVED_MANIFEST") or None


def package_path(run_id: str) -> Path:
    return MODEL_ROOT / "candidates" / str(UUID(run_id))


async def selected_manifest(session, version: str) -> str | None:
    if version == INITIAL:
        return initial_manifest()
    run = await session.get(TrainingRun, UUID(version))
    if run is None or run.model_family != "image_segmentation" or not run.config.get("package"):
        raise ValueError("Selected wrinkle model is unavailable")
    return str(package_path(version) / "approved.json")


async def check_lineage(session, version: str, *, verify_files=True):
    """Fine-tuned weights inherit every ancestor's dataset and consent obligations."""
    seen = set()
    while version != INITIAL:
        if version in seen or len(seen) >= 100:
            raise ValueError("Invalid model lineage")
        seen.add(version)
        run = await session.get(TrainingRun, UUID(version))
        if run is None:
            raise ValueError("Model lineage is missing")
        if verify_files:
            await checked_dataset(session, run.dataset_uri)
        else:
            manifest, _ = await asyncio.to_thread(dataset_path, run.dataset_uri)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data["source"] == "consented_user_review":
                from backend.services.wrinkle_datasets import check_user_dataset

                await check_user_dataset(session, data)
        version = run.config["base_version"]


def quality_gate(result: dict) -> dict:
    # Fixed before training; no client-supplied thresholds can lower the release bar.
    candidate, baseline = result.get("candidate", {}), result.get("baseline", {})
    reasons = []
    for split in ("validation", "test"):
        if candidate.get(f"{split}_positive_samples", 0) < 1:
            reasons.append(f"{split}: at least one reviewed positive sample is required")
        for metric in ("dice", "iou", "mean_dice"):
            key = f"{split}_{metric}"
            new, old = candidate.get(key), baseline.get(key)
            if (
                not isinstance(new, int | float)
                or not math.isfinite(new)
                or not isinstance(old, int | float)
                or not math.isfinite(old)
                or not 0 <= new <= 1
                or not 0 <= old <= 1
                or new < old
            ):
                reasons.append(f"{key}: candidate must match or improve the incumbent")
        if candidate.get(f"{split}_dice", 0) < 0.60:
            reasons.append(f"{split}: Dice must be at least 0.60")
    return {"passed": not reasons, "reasons": reasons, "minimum_dice": 0.60}


async def checked_dataset(session, uri: str) -> tuple[Path, dict]:
    manifest, _ = await asyncio.to_thread(dataset_path, uri)
    await asyncio.to_thread(validate_manifest, manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data["source"] == "consented_user_review":
        from backend.services.wrinkle_datasets import check_user_dataset

        await check_user_dataset(session, data)
    return manifest, data


async def submit(session, uri: str, epochs: int, expected_active: str, actor: str):
    await checked_dataset(session, uri)
    row = await deployment(session, lock=True)
    if row.state["active"] != expected_active or row.state.get("pending"):
        raise HTTPException(409, "Model changed or deployment is pending; refresh")
    await check_lineage(session, expected_active)
    busy = await session.scalar(
        select(TrainingRun.id).where(
            TrainingRun.model_family.in_(["image_segmentation", "wrinkle_dataset"]),
            TrainingRun.status.in_(["queued", "running"]),
        )
    )
    if busy:
        raise HTTPException(409, "A wrinkle training run is already queued or running")
    run = TrainingRun(
        model_family="image_segmentation",
        dataset_uri=uri,
        config={
            "epochs": epochs,
            "wrinkle_admin": True,
            "base_version": expected_active,
            "base_manifest": await selected_manifest(session, expected_active),
            "actor": actor,
            "requested_at": now(),
            "epoch": 0,
        },
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    try:
        redis = await get_arq_pool()
        try:
            job = await enqueue_job(
                redis,
                "run_training",
                str(run.id),
                _queue_name="training",
                _job_id=f"wrinkle-{run.id}",
            )
            if job is None:
                raise RuntimeError("Training queue did not accept the job")
        finally:
            await redis.close()
    except Exception as error:
        run.status = "failed"
        run.config = {**run.config, "error": "Training queue unavailable; retry"}
        await session.commit()
        raise HTTPException(503, "Training queue unavailable; retry") from error
    return run


def run_summary(run) -> dict:
    config = run.config
    return {
        "id": str(run.id),
        "status": run.status,
        "dataset_uri": run.dataset_uri,
        "mlflow_run_id": run.mlflow_run_id,
        "created_at": run.created_at,
        **{
            key: config.get(key)
            for key in (
                "epochs",
                "epoch",
                "loss",
                "base_version",
                "actor",
                "error",
                "evaluation",
                "gate",
            )
        },
        "calibrated": bool(config.get("policy_hashes")),
    }


async def request_activation(session, version: str, expected_active: str, actor: str, action: str):
    row = await deployment(session, lock=True)
    if row.state["active"] != expected_active or row.state.get("pending"):
        raise HTTPException(409, "Model changed or deployment is pending; refresh")
    if version == expected_active:
        raise HTTPException(409, "This version is already selected")
    if action == "rollback":
        history = row.state.get("history", [])
        if not history or version != history[-1]["from"]:
            raise HTTPException(409, "Rollback target changed; refresh")
    else:
        run = await session.get(TrainingRun, UUID(version))
        if (
            run is None
            or run.status != "awaiting_approval"
            or run.config.get("base_version") != expected_active
            or not quality_gate(run.config.get("evaluation", {}))["passed"]
        ):
            raise HTTPException(409, "Candidate is not eligible for approval")
    if version != INITIAL:
        run = await session.get(TrainingRun, UUID(version))
        if run is None:
            raise HTTPException(404, "Model not found")
        await checked_dataset(session, run.dataset_uri)
        await check_lineage(session, version)
    pending = {
        "version": version,
        "expected_active": expected_active,
        "actor": actor,
        "action": action,
        "at": now(),
    }
    row.state = {**row.state, "pending": pending, "error": None}
    await session.commit()
    try:
        redis = await get_arq_pool()
        try:
            job = await enqueue_job(redis, "activate_wrinkle", pending, _queue_name="training")
            if job is None:
                raise RuntimeError("Deployment queue did not accept the job")
        finally:
            await redis.close()
    except Exception as error:
        row.state = {**row.state, "pending": None, "error": "Deployment queue unavailable"}
        await session.commit()
        raise HTTPException(503, "Deployment queue unavailable; retry") from error


async def reconcile(session):
    runs = (
        await session.scalars(
            select(TrainingRun).where(
                TrainingRun.model_family.in_(["image_segmentation", "wrinkle_dataset"]),
                TrainingRun.status.in_(["queued", "running"]),
            )
        )
    ).all()
    for run in runs:
        last = run.config.get("heartbeat", run.config.get("requested_at"))
        if last and datetime.fromisoformat(last) < datetime.now(UTC) - timedelta(hours=7):
            run.status = "failed"
            run.config = {**run.config, "error": "Training worker stopped; retry"}
    row = await deployment(session, lock=True)
    pending = row.state.get("pending")
    if pending and datetime.fromisoformat(pending["at"]) < datetime.now(UTC) - timedelta(
        minutes=30
    ):
        row.state = {**row.state, "pending": None, "error": "Deployment timed out; retry"}
    await session.commit()
