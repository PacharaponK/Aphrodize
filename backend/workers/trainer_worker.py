import asyncio
import json
import logging
from datetime import UTC
from threading import Event
from uuid import UUID

import mlflow
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from backend.core.config import settings
from backend.core.db.models import TrainingRun
from backend.core.db.session import SessionLocal, close_database
from backend.core.observability import observed_job, start_worker_metrics, stop_worker_metrics
from backend.libs.redis_client import redis_settings
from backend.services import wrinkle_lifecycle as wrinkle
from backend.services.curated_training import PREPROCESSING_VERSION, train_candidate
from backend.services.daily_health_tracking import track_daily_health_candidate
from backend.services.daily_health_training import (
    enqueue_candidate_training_if_ready,
    train_daily_health_candidate,
)

logger = logging.getLogger(__name__)


def _train_with_mlflow(run: TrainingRun, progress=None, check_consent=None, cancelled=None) -> str:
    """Train one validated image candidate inside a traceable MLflow run."""
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    with mlflow.start_run(run_name=f"aphrodize-{run.model_family}") as mlflow_run:
        mlflow.log_params({"model_family": run.model_family, **run.config})
        mlflow.set_tag("dataset_uri", run.dataset_uri)
        if run.config.get("wrinkle_admin"):
            if progress:
                progress({"mlflow_run_id": mlflow_run.info.run_id})
            result = train_candidate(
                run.dataset_uri,
                epochs=run.config["epochs"],
                base_manifest=run.config.get("base_manifest"),
                check_consent=check_consent,
                cancelled=cancelled,
                progress=(lambda epoch, loss: progress({"epoch": epoch, "loss": loss}))
                if progress
                else None,
            )
            directory = wrinkle.package_path(str(run.id))
            directory.mkdir(parents=True, exist_ok=True)
            checkpoint = mlflow.artifacts.download_artifacts(
                run_id=mlflow_run.info.run_id,
                artifact_path="model/candidate_unet.pth",
                dst_path=str(directory),
            )
            from pathlib import Path

            from backend.services.curated_training import sha256_file

            checkpoint = Path(checkpoint)
            target = directory / "candidate_unet.pth"
            if checkpoint != target:
                checkpoint.replace(target)
            run.config = {
                **run.config,
                "evaluation": result,
                "gate": wrinkle.quality_gate(result),
                "checkpoint_sha256": sha256_file(target),
                "package": True,
                "epoch": run.config["epochs"],
            }
        else:
            options = (
                {"check_consent": check_consent, "cancelled": cancelled} if check_consent else {}
            )
            train_candidate(run.dataset_uri, epochs=run.config.get("epochs", 1), **options)
        return mlflow_run.info.run_id


async def shutdown(ctx: dict) -> None:
    await stop_worker_metrics(ctx)
    await close_database()


@observed_job
async def run_training(ctx: dict, training_run_id: str) -> None:
    """Train approved image datasets; keep other model families as placeholders."""
    async with SessionLocal() as session:
        # Fetch the request saved by training_service before it entered Redis.
        run = await session.scalar(
            select(TrainingRun)
            .where(
                TrainingRun.id == UUID(training_run_id),
            )
            .with_for_update()
        )
        if run is None or run.status != "queued":
            ctx["telemetry_outcome"] = "skipped"
            return
        run.status = "running"
        run.config = {**run.config, "heartbeat": wrinkle.now()}
        await session.commit()
        cancellation = Event()
        try:
            if run.model_family == "image_segmentation":
                loop = asyncio.get_running_loop()

                async def update(fields):
                    async with SessionLocal() as progress_session:
                        current = await progress_session.get(TrainingRun, run.id)
                        if "mlflow_run_id" in fields:
                            current.mlflow_run_id = fields["mlflow_run_id"]
                        current.config = {**current.config, **fields, "heartbeat": wrinkle.now()}
                        await progress_session.commit()

                async def check():
                    async with SessionLocal() as consent_session:
                        await wrinkle.checked_dataset(consent_session, run.dataset_uri)
                        await wrinkle.check_lineage(
                            consent_session,
                            run.config.get("base_version", wrinkle.INITIAL),
                        )

                def progress(fields):
                    asyncio.run_coroutine_threadsafe(update(fields), loop).result(timeout=60)

                def check_consent():
                    asyncio.run_coroutine_threadsafe(check(), loop).result(timeout=60)

                await check()
                # Real image training runs off the async event loop.
                run.mlflow_run_id = await asyncio.to_thread(
                    _train_with_mlflow,
                    run,
                    progress,
                    check_consent,
                    cancellation.is_set,
                )
                # Training success never deploys the candidate automatically.
                run.status = "awaiting_approval"
            elif run.model_family == "wrinkle_dataset":
                from backend.services.wrinkle_datasets import build_dataset

                run.dataset_uri = await build_dataset(session, run)
                run.status = "ready"
            else:
                # Other model families currently record metadata only.
                mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
                with mlflow.start_run(run_name=f"aphrodize-{run.model_family}") as mlflow_run:
                    mlflow.log_params({"model_family": run.model_family, **run.config})
                    mlflow.set_tag("dataset_uri", run.dataset_uri)
                    mlflow.set_tag("execution_kind", "metadata_only")
                    mlflow.set_tag("training_executed", "false")
                    run.mlflow_run_id = mlflow_run.info.run_id
                    run.status = "awaiting_model_package"
        except asyncio.CancelledError:
            cancellation.set()
            run.status = "failed"
            run.config = {**run.config, "error": "Training timed out or worker stopped; retry"}
            await session.commit()
            raise
        except Exception:
            # Keep internal error details in logs and expose a failed status.
            logger.exception("Training run %s failed", training_run_id)
            run.status = "failed"
            run.config = {**run.config, "error": "Worker failed; check service logs and retry"}
            ctx["telemetry_outcome"] = "failed"
        await session.commit()


def checkpoint_hash(manifest):
    from ai.ffhq_wrinkle.modeling import default_checkpoint
    from backend.services.curated_training import sha256_file
    from backend.wrinkle.approved_model import approved_checkpoint

    return sha256_file(approved_checkpoint(manifest) if manifest else default_checkpoint("UNet"))


def smoke_checkpoint(manifest, expected_sha=None):
    import torch

    from ai.ffhq_wrinkle.modeling import load_wrinkle_model
    from backend.services.curated_training import sha256_file
    from backend.wrinkle.approved_model import approved_checkpoint

    path = approved_checkpoint(manifest) if manifest else None
    if path and expected_sha and sha256_file(path) != expected_sha:
        raise ValueError("Candidate checkpoint changed")
    bundle = load_wrinkle_model("UNet", checkpoint_path=path, verify_official=not bool(path))
    with torch.inference_mode():
        logits = bundle.model(torch.zeros((1, 4, 128, 128), device=bundle.device))
        if logits.shape != (1, 2, 128, 128) or not torch.isfinite(logits).all():
            raise ValueError("Candidate smoke inference failed")


@observed_job
async def activate_wrinkle(ctx, pending):
    async with SessionLocal() as session:
        row = await wrinkle.deployment(session, lock=True)
        if row.state.get("pending") != pending or row.state["active"] != pending["expected_active"]:
            await session.commit()
            return
        try:
            version = pending["version"]
            digest = None
            if version != wrinkle.INITIAL:
                run = await session.get(TrainingRun, UUID(version))
                if run is None or not run.config.get("package"):
                    raise ValueError("Candidate package is unavailable")
                _, data = await wrinkle.checked_dataset(session, run.dataset_uri)
                await wrinkle.check_lineage(session, version)
                if pending["action"] == "promote" and (
                    run.config.get("base_version") != row.state["active"]
                    or not wrinkle.quality_gate(run.config.get("evaluation", {}))["passed"]
                ):
                    raise ValueError("Candidate quality gate changed")
                if pending["action"] == "promote":
                    base_manifest = await wrinkle.selected_manifest(session, row.state["active"])
                    base_hash = await asyncio.to_thread(checkpoint_hash, base_manifest)
                    if base_hash != run.config["evaluation"]["base_checkpoint_sha256"]:
                        raise ValueError("Incumbent checkpoint changed after training")
                digest = run.config["checkpoint_sha256"]
                directory = wrinkle.package_path(version)
                policy = directory / "policy"
                policy_hashes = {}
                if policy.is_dir():
                    from ai.ffhq_wrinkle.calibration import load_released_policy_bundle
                    from backend.services.curated_training import sha256_file

                    calibrated = load_released_policy_bundle(policy)
                    if calibrated.checkpoint_sha256 != digest:
                        raise ValueError("Confidence policy belongs to a different checkpoint")
                    policy_hashes = {
                        name: sha256_file(policy / name)
                        for name in (
                            "candidate_confidence_policy.json",
                            "calibration_report.json",
                        )
                    }
                run.config = {**run.config, "policy_hashes": policy_hashes}
                manifest = directory / "approved.json"
                manifest.write_text(
                    json.dumps(
                        {
                            "status": "approved",
                            "architecture": "UNet",
                            "preprocessing_version": PREPROCESSING_VERSION,
                            "checkpoint": "candidate_unet.pth",
                            "checkpoint_sha256": digest,
                            "approval_reference": f"admin:{pending['actor']}:{pending['at']}",
                            "rights_reference": data["rights_reference"],
                        }
                    ),
                    encoding="utf-8",
                )
            else:
                manifest = wrinkle.initial_manifest()
            await asyncio.to_thread(smoke_checkpoint, manifest, digest)
            # Recheck after model loading, before committing the deployment pointer.
            if version != wrinkle.INITIAL:
                await wrinkle.checked_dataset(session, run.dataset_uri)
                await wrinkle.check_lineage(session, version)
            row.state = {
                **row.state,
                "active": version,
                "pending": None,
                "error": None,
                "history": [
                    *row.state["history"],
                    {
                        "from": row.state["active"],
                        "to": version,
                        "actor": pending["actor"],
                        "action": pending["action"],
                        "at": wrinkle.now(),
                    },
                ],
            }
        except Exception:
            logger.exception("Wrinkle deployment failed")
            row.state = {**row.state, "pending": None, "error": "Model verification failed; retry"}
            ctx["telemetry_outcome"] = "failed"
        await session.commit()


async def reconcile_wrinkle_jobs(_):
    from backend.services.wrinkle_datasets import cleanup_datasets

    async with SessionLocal() as session:
        await wrinkle.reconcile(session)
        await cleanup_datasets(session)


@observed_job
async def run_daily_health_candidate_training(_: dict) -> None:
    """Create a review-only version when enough consented self-reports have arrived."""
    async with SessionLocal() as session:
        version = await train_daily_health_candidate(session)
        if version is not None and version.status == "candidate" and not version.mlflow_run_id:
            # Keep MLflow I/O outside the worker event loop. A tracking outage must
            # not discard an already-persisted candidate or activate it.
            try:
                version.mlflow_run_id = await asyncio.to_thread(
                    track_daily_health_candidate, version
                )
                await session.commit()
            except Exception as error:
                logger.warning("Candidate tracking unavailable: %s", type(error).__name__)
                raise


@observed_job
async def check_daily_health_candidate_training(_: dict) -> None:
    """Weekly: queue a candidate run only if the consented cohort passes readiness checks."""
    async with SessionLocal() as session:
        await enqueue_candidate_training_if_ready(session)


class WorkerSettings:
    max_jobs = 1
    job_timeout = 6 * 60 * 60
    functions = [run_training, run_daily_health_candidate_training, activate_wrinkle]
    # Monday 02:00 UTC is Monday 09:00 in the tracker’s Asia/Bangkok timezone.
    timezone = UTC
    cron_jobs = [
        cron(reconcile_wrinkle_jobs, minute=0, run_at_startup=True),
        cron(
            check_daily_health_candidate_training,
            weekday="mon",
            hour=2,
            minute=0,
            run_at_startup=False,
        ),
    ]
    on_shutdown = shutdown
    on_startup = start_worker_metrics
    health_check_interval = 30
    redis_settings: RedisSettings = redis_settings()
    queue_name = "training"
