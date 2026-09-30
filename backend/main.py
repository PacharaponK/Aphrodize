import logging
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import api_router
from backend.core.config import settings
from backend.core.db.session import close_database, create_database_schema
from backend.libs.minio_client import ensure_bucket

logger = logging.getLogger(__name__)


def _ensure_storage_buckets_when_reachable() -> None:
    host, separator, raw_port = settings.minio_endpoint.rpartition(":")
    if not separator or not host:
        logger.warning("MinIO endpoint is invalid; starting without image storage")
        return
    try:
        with socket.create_connection((host, int(raw_port)), timeout=0.5):
            pass
    except (OSError, ValueError):
        logger.warning("MinIO is not reachable; starting without image storage")
        return

    try:
        ensure_bucket()
    except Exception:
        # Account and health APIs should remain available while optional image
        # storage is recovering; image-dependent endpoints still require MinIO.
        logger.exception(
            "Object storage bucket setup failed; continuing with account APIs only"
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_database_schema()
    _ensure_storage_buckets_when_reachable()
    try:
        yield
    finally:
        await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "A privacy-first ML workflow API for time-series and non-time-series models. "
        "It is not a diagnostic service."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
app.include_router(api_router, prefix="/api/v1")
