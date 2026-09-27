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
        if connection.dialect.name == "postgresql":
            # Widen the existing check without touching stored daily-health rows.
            constraint_definition = await connection.scalar(
                text(
                    "SELECT pg_get_constraintdef(oid) "
                    "FROM pg_constraint "
                    "WHERE conrelid = 'daily_health_entries'::regclass "
                    "AND conname = 'ck_daily_health_sleep_duration'"
                )
            )
            if constraint_definition is None or "<= 600" not in constraint_definition:
                await connection.execute(
                    text(
                        "ALTER TABLE daily_health_entries "
                        "DROP CONSTRAINT IF EXISTS ck_daily_health_sleep_duration"
                    )
                )
                await connection.execute(
                    text(
                        "ALTER TABLE daily_health_entries "
                        "ADD CONSTRAINT ck_daily_health_sleep_duration "
                        "CHECK (sleep_duration_minutes >= 0 AND sleep_duration_minutes <= 600)"
                    )
                )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_outcomes "
                    "ADD COLUMN IF NOT EXISTS reported_dryness_level_0_10 FLOAT"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries "
                    "ADD COLUMN IF NOT EXISTS prediction_target_date DATE"
                )
            )
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conname = 'ck_daily_health_reported_dryness_level' "
                    "AND conrelid = 'daily_health_outcomes'::regclass) THEN "
                    "ALTER TABLE daily_health_outcomes "
                    "ADD CONSTRAINT ck_daily_health_reported_dryness_level "
                    "CHECK (reported_dryness_level_0_10 IS NULL OR "
                    "(reported_dryness_level_0_10 >= 0 AND "
                    "reported_dryness_level_0_10 <= 10)); "
                    "END IF; END $$;"
                )
            )


async def close_database() -> None:
    await engine.dispose()
