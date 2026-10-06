"""Small privacy-safe inference summary for the local model operator."""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.db.models import Analysis
from backend.core.db.session import get_session
from backend.services.uv_lifecycle import ARTIFACTS, read_json
from backend.services.uv_service import load_recommendation

router = APIRouter()


@router.get("/uv")
async def uv_health() -> dict:
    try:
        forecasts = {
            city: load_recommendation(city) for city in ("bangkok", "songkhla", "chiang_mai")
        }
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    try:
        quality = read_json(ARTIFACTS / "monitoring.json")
        updated = datetime.fromisoformat(quality["generated_at"])
        if updated.tzinfo is None or not timedelta(minutes=-5) <= datetime.now(
            UTC
        ) - updated <= timedelta(hours=8):
            quality = {"status": "stale"}
    except (OSError, ValueError, KeyError, TypeError):
        quality = {"status": "unavailable"}
    try:
        training = read_json(ARTIFACTS / "pipeline_status.json")
        training = {
            key: training[key]
            for key in ("at", "status", "version", "gate_passed", "error_type")
            if key in training
        }
    except (OSError, ValueError, TypeError):
        training = {"status": "unavailable"}
    return {
        "status": "fresh",
        "quality": quality,
        "training": training,
        "cities": {
            city: {
                "data_date": value["data_date"],
                "generated_at": value["generated_at"],
                "model_version": value["model_version"],
                "weather_available": [day["weather"] is not None for day in value["days"]],
            }
            for city, value in forecasts.items()
        },
    }


def summarize_analyses(rows: list[Analysis]) -> dict:
    models = defaultdict(lambda: {"status": Counter(), "quality_flags": Counter(), "latency": []})
    for row in rows:
        record = models[row.model_version]
        record["status"][row.status.value] += 1
        record["quality_flags"].update(row.quality_flags or [])
        if row.completed_at:
            created = (
                row.created_at.replace(tzinfo=UTC)
                if row.created_at.tzinfo is None
                else row.created_at
            )
            completed = (
                row.completed_at.replace(tzinfo=UTC)
                if row.completed_at.tzinfo is None
                else row.completed_at
            )
            record["latency"].append(max(0.0, (completed - created).total_seconds()))
    result = {}
    for version, record in models.items():
        latency = sorted(record["latency"])
        status = record["status"]
        p95 = latency[max(0, (95 * len(latency) + 99) // 100 - 1)] if latency else None
        result[version] = {
            "status": dict(status),
            "quality_flags": dict(record["quality_flags"]),
            "failure_rate": status["failed"] / max(1, sum(status.values())),
            "p95_seconds": p95,
        }
    return {"sample_count": len(rows), "models": result}


@router.get("/analyses")
async def analysis_health(
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # ponytail: cap the local pilot scan; use a metrics store when traffic exceeds 5000/week.
    rows = list(
        (
            await session.scalars(
                select(Analysis)
                .where(Analysis.created_at >= datetime.now(UTC) - timedelta(hours=hours))
                .order_by(Analysis.created_at.desc())
                .limit(5000)
            )
        ).all()
    )
    return summarize_analyses(rows)
