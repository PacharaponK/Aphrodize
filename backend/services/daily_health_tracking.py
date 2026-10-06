"""Aggregate-only experiment tracking; no participant rows or model copies."""

import math

from mlflow.tracking import MlflowClient

from backend.core.config import settings


def track_daily_health_candidate(version) -> str:
    client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    experiment = client.get_experiment_by_name("daily-health-next-day")
    experiment_id = (
        experiment.experiment_id if experiment is not None
        else client.create_experiment("daily-health-next-day")
    )
    run = client.create_run(experiment_id, tags={
        "mlflow.runName": version.version_id,
        "model_family": version.model_family,
        "registry_version_id": version.version_id,
        "review_status": "candidate_not_deployed",
        "tracking_scope": "aggregate_metrics_only",
        "data_origin": "consented_user_reported_outcomes",
    })
    run_id = run.info.run_id
    try:
        client.log_param(run_id, "training_records", version.training_records)
        client.log_param(run_id, "participant_count", version.participant_count)
        client.log_param(run_id, "prediction_horizon_days", 1)
        for split, targets in (version.metrics or {}).items():
            if not isinstance(targets, dict):
                continue
            for target, scores in targets.items():
                if not isinstance(scores, dict):
                    continue
                for metric, value in scores.items():
                    if type(value) in (int, float) and math.isfinite(value):
                        client.log_metric(run_id, f"{split}.{target}.{metric}", value)
        client.set_terminated(run_id, status="FINISHED")
    except Exception:
        client.set_terminated(run_id, status="FAILED")
        raise
    return run_id
