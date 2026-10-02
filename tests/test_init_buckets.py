from backend.core.config import settings
from backend.scripts import init_buckets


def test_initializer_creates_every_bucket_used_by_the_stack(monkeypatch) -> None:
    created: list[str] = []

    class EmptyObjectStore:
        def bucket_exists(self, bucket: str) -> bool:
            return False

        def make_bucket(self, bucket: str) -> None:
            created.append(bucket)

    monkeypatch.setattr(init_buckets, "get_minio_client", EmptyObjectStore)

    init_buckets.initialize_buckets()

    assert set(created) == {
        settings.minio_bucket,
        settings.annotation_bucket,
        "mlflow",
    }
