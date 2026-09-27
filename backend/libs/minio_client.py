from io import BytesIO
from uuid import UUID

from minio import Minio

from backend.core.config import settings


def analysis_artifact_key(user_id: UUID, analysis_id: UUID, kind: str) -> str:
    # Only the two user-facing result images may use this derived key layout.
    if kind not in {"overlay", "mask"}:
        raise ValueError("unsupported analysis artifact")
    return f"users/{user_id}/derived/{analysis_id}/{kind}.png"


def annotation_image_key(user_id: UUID, analysis_id: UUID) -> str:
    # Review images have their own key namespace; callers select the review bucket.
    return f"users/{user_id}/annotation/{analysis_id}/aligned_face.png"


def get_minio_client() -> Minio:
    # Read the private object-store connection from process configuration.
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    # Both analysis artifacts and review images need buckets before jobs run.
    client = get_minio_client()
    for bucket in (settings.minio_bucket, settings.annotation_bucket):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def put_bytes(
    object_key: str, payload: bytes, content_type: str, bucket: str | None = None
) -> None:
    # Use the analysis bucket by default; callers can request the review bucket.
    get_minio_client().put_object(
        bucket or settings.minio_bucket,
        object_key,
        BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )


def get_bytes(object_key: str, bucket: str | None = None) -> bytes:
    # Read object bytes and release the HTTP connection even after a read failure.
    response = get_minio_client().get_object(bucket or settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def remove_objects(object_keys: list[str], bucket: str | None = None) -> None:
    # Remove each requested object from the selected private bucket.
    for object_key in object_keys:
        get_minio_client().remove_object(bucket or settings.minio_bucket, object_key)
