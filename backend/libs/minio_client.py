from io import BytesIO
from uuid import UUID

from minio import Minio

from backend.core.config import settings


def analysis_artifact_key(user_id: UUID, analysis_id: UUID, kind: str) -> str:
    if kind not in {"overlay", "mask"}:
        raise ValueError("unsupported analysis artifact")
    return f"users/{user_id}/derived/{analysis_id}/{kind}.png"


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def put_bytes(object_key: str, payload: bytes, content_type: str) -> None:
    get_minio_client().put_object(
        settings.minio_bucket,
        object_key,
        BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )


def get_bytes(object_key: str) -> bytes:
    response = get_minio_client().get_object(settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def remove_objects(object_keys: list[str]) -> None:
    for object_key in object_keys:
        get_minio_client().remove_object(settings.minio_bucket, object_key)
