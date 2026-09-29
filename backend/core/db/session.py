from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.core.db.base import Base

engine = create_async_engine(settings.resolved_database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def create_database_schema() -> None:
    from backend.core.db import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        # create_all creates new tables but never adds fields to an existing local
        # development database.  This nullable provenance field is safe to add
        # without inventing a target date for historical predictions.
        await connection.execute(
            text(
                "ALTER TABLE daily_health_entries "
                "ADD COLUMN IF NOT EXISTS prediction_target_date DATE"
            )
        )


async def close_database() -> None:
    await engine.dispose()
