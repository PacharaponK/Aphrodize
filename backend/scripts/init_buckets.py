"""Create the private application and MLflow artifact buckets once MinIO is ready."""

import time

from backend.core.config import settings
from backend.libs.minio_client import get_minio_client

BUCKETS = (settings.minio_bucket, "mlflow")
MAX_ATTEMPTS = 30


def initialize_buckets() -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            client = get_minio_client()
            for bucket in BUCKETS:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
            return
        except Exception as error:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError("MinIO was not ready for bucket initialization") from error
            time.sleep(2)


if __name__ == "__main__":
    initialize_buckets()
