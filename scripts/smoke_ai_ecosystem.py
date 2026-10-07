"""Retained development smoke runs; never promote or use private user data."""

import base64
import json
import os
import tempfile
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import joblib
import mlflow
import numpy as np
from minio import Minio
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from backend.core.config import settings


def api(path, payload=None):
    token = base64.b64encode(
        f"{settings.api_username}:{settings.api_password}".encode()
    ).decode()
    request = Request(
        f"http://localhost:8000/api/v1{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def main():
    # These secrets remain process-local, never printed or recorded in MLflow.
    os.environ["AWS_ACCESS_KEY_ID"] = settings.minio_access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.minio_secret_key
    scheme = "https" if settings.minio_secure else "http"
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"{scheme}://{settings.minio_endpoint}"
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("development-connectivity")
    rng = np.random.default_rng(42)
    x = rng.normal(size=(120, 3))
    y = 2 * x[:, 0] - x[:, 1] + rng.normal(scale=0.1, size=120)
    train_x, test_x, train_y, test_y = train_test_split(x, y, random_state=42)
    with mlflow.start_run(run_name="synthetic-training-storage-smoke") as run:
        mlflow.set_tags({
            "purpose": "connectivity_test", "data_origin": "synthetic",
            "deployment_eligible": "false", "production_pipeline": "false",
            "artifact_transfer": "minio_sdk_host_smoke",
        })
        mlflow.log_params({"seed": 42, "records": 120, "n_estimators": 20})
        model = RandomForestRegressor(n_estimators=20, random_state=42, n_jobs=1)
        model.fit(train_x, train_y)
        mae = float(mean_absolute_error(test_y, model.predict(test_x)))
        mlflow.log_metric("synthetic_holdout_mae", mae)
        with tempfile.TemporaryDirectory(prefix="aphrodize-mlflow-smoke-") as directory:
            artifact = Path(directory) / "synthetic-test-model.joblib"
            joblib.dump(model, artifact)
            # The host venv lacks boto3; use the installed MinIO SDK against the
            # exact S3 artifact URI returned by MLflow, without changing the store.
            location = urlparse(run.info.artifact_uri)
            if location.scheme != "s3":
                raise RuntimeError("This smoke test requires the configured S3 artifact store")
            client = Minio(
                "localhost:9000", access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key, secure=False,
            )
            key = location.path.strip("/") + "/smoke-only/synthetic-test-model.joblib"
            client.fput_object(location.netloc, key, str(artifact))
            response = client.get_object(location.netloc, key)
            try:
                restored = joblib.load(BytesIO(response.read()))
            finally:
                response.close()
                response.release_conn()
            assert np.allclose(model.predict(test_x), restored.predict(test_x))
        print(json.dumps({
            "synthetic_training_run": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "artifact_roundtrip": "passed", "synthetic_holdout_mae": mae,
        }))

    # The generic time_series worker currently logs metadata only; do not label it training.
    queued = api("/training/runs", {
        "model_family": "time_series", "dataset_uri": "smoke://synthetic-metadata-only",
        "config": {"purpose": "connectivity_test", "deployment_eligible": False},
    })
    run_id = queued["id"]
    result = queued
    for _ in range(15):
        result = api(f"/training/runs/{run_id}")
        if result["status"] not in ("queued", "running"):
            break
        time.sleep(2)
    print(json.dumps({
        "api_arq_training_request": run_id,
        "status": result["status"], "mlflow_run_id": result.get("mlflow_run_id"),
        "test_kind": "metadata_only_not_retraining",
    }))


if __name__ == "__main__":
    main()
