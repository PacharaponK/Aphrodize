"""Run inside the API container; check data services without logging credentials."""

import asyncio

from redis.asyncio import Redis
from sqlalchemy import text

from backend.core.config import settings
from backend.core.db.session import engine
from backend.libs.minio_client import get_minio_client


async def check():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        redis = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            socket_timeout=5,
        )
        try:
            if not await redis.ping():
                raise RuntimeError("Redis unavailable")
        finally:
            await redis.aclose()
        client = get_minio_client()
        for bucket in (settings.minio_bucket, settings.annotation_bucket):
            if not await asyncio.to_thread(client.bucket_exists, bucket):
                raise RuntimeError("Required bucket unavailable")
    finally:
        await engine.dispose()


try:
    asyncio.run(asyncio.wait_for(check(), timeout=30))
except Exception:
    raise SystemExit("Data-service readiness check failed") from None
