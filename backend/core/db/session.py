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
            # create_all creates new tables but never adds fields to existing ones.
            # These additive statements bring older local databases forward without
            # dropping tables or changing existing user records.
            await connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active'"
                )
            )
            await connection.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL")
            )
            await connection.execute(
                text(
                    """
                    DO $migration$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'ck_users_status'
                              AND conrelid = 'users'::regclass
                        ) THEN
                            ALTER TABLE users
                            ADD CONSTRAINT ck_users_status
                            CHECK (status IN ('active', 'suspended', 'deleted'));
                        END IF;
                    END
                    $migration$;
                    """
                )
            )

            account_columns = (
                "email_verified_at TIMESTAMPTZ NULL",
                "password_updated_at TIMESTAMPTZ NULL",
                "last_login_at TIMESTAMPTZ NULL",
                "failed_login_count INTEGER NOT NULL DEFAULT 0",
                "locked_until TIMESTAMPTZ NULL",
                "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
            )
            for column in account_columns:
                await connection.execute(
                    text(f"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS {column}")
                )

            # This nullable provenance field does not invent target dates for
            # historical predictions.
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries "
                    "ADD COLUMN IF NOT EXISTS prediction_target_date DATE"
                )
            )


async def close_database() -> None:
    await engine.dispose()
