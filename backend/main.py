from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.v1.router import api_router
from backend.core.config import settings
from backend.core.db.session import close_database, create_database_schema
from backend.libs.minio_client import ensure_bucket


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_database_schema()
    ensure_bucket()
    yield
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
app.include_router(api_router, prefix="/api/v1")
