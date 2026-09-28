from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
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
        if connection.dialect.name == "sqlite":
            profile_columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("daily_health_profiles")
                }
            )
            if "weight_kg" not in profile_columns:
                await connection.execute(
                    text("ALTER TABLE daily_health_profiles ADD COLUMN weight_kg FLOAT")
                )
        if connection.dialect.name == "postgresql":
            # Refuse to discard historical rows from another deployment.
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF to_regclass('public.daily_lifestyle_observations') IS NOT NULL THEN "
                    "IF EXISTS (SELECT 1 FROM daily_lifestyle_observations) THEN "
                    "RAISE EXCEPTION 'Legacy lifestyle observations need export before removal'; "
                    "END IF; "
                    "DROP TABLE daily_lifestyle_observations; "
                    "END IF; END $$;"
                )
            )
            # Existing installations predate the account lifecycle fields on users.
            await connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active'"
                )
            )
            await connection.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ")
            )
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conrelid = 'users'::regclass AND conname = 'ck_users_status') THEN "
                    "ALTER TABLE users ADD CONSTRAINT ck_users_status "
                    "CHECK (status IN ('active', 'suspended', 'deleted')); "
                    "END IF; END $$;"
                )
            )
            # create_all does not add columns to an accounts table created by older builds.
            for column in (
                "email_verified_at TIMESTAMPTZ",
                "password_updated_at TIMESTAMPTZ",
                "last_login_at TIMESTAMPTZ",
                "failed_login_count INTEGER NOT NULL DEFAULT 0",
                "locked_until TIMESTAMPTZ",
                "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
            ):
                await connection.execute(
                    text(f"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS {column}")
                )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_profiles "
                    "ADD COLUMN IF NOT EXISTS skin_type VARCHAR(32)"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_profiles "
                    "ADD COLUMN IF NOT EXISTS weight_kg FLOAT"
                )
            )
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conname = 'ck_daily_health_profile_skin_type' "
                    "AND conrelid = 'daily_health_profiles'::regclass) THEN "
                    "ALTER TABLE daily_health_profiles "
                    "ADD CONSTRAINT ck_daily_health_profile_skin_type CHECK "
                    "(skin_type IS NULL OR skin_type IN "
                    "('normal', 'dry', 'oily', 'combination', 'sensitive', 'prefer_not_to_say')); "
                    "END IF; END $$;"
                )
            )
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conname = 'ck_daily_health_profile_weight' "
                    "AND conrelid = 'daily_health_profiles'::regclass) THEN "
                    "ALTER TABLE daily_health_profiles "
                    "ADD CONSTRAINT ck_daily_health_profile_weight CHECK "
                    "(weight_kg IS NULL OR (weight_kg >= 1 AND weight_kg <= 500)); "
                    "END IF; END $$;"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries ADD COLUMN IF NOT EXISTS weight_kg FLOAT "
                    "CONSTRAINT ck_daily_health_weight CHECK (weight_kg >= 1 AND weight_kg <= 500)"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries "
                    "ADD COLUMN IF NOT EXISTS calculated_thirst_score_0_10 FLOAT "
                    "CONSTRAINT ck_daily_health_calculated_thirst "
                    "CHECK (calculated_thirst_score_0_10 >= 0 "
                    "AND calculated_thirst_score_0_10 <= 10)"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries "
                    "ADD COLUMN IF NOT EXISTS thirst_score_method VARCHAR(64)"
                )
            )
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
            # Retired entry labels were never written by the current API. Refuse to
            # discard values from an older deployment without a deliberate backfill.
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF EXISTS (SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'daily_health_entries' "
                    "AND column_name = 'reported_thirst_score_0_10') THEN "
                    "IF EXISTS (SELECT 1 FROM daily_health_entries "
                    "WHERE reported_thirst_score_0_10 IS NOT NULL "
                    "OR reported_dryness_score_0_10 IS NOT NULL) THEN "
                    "RAISE EXCEPTION 'Legacy daily-health labels need manual migration'; "
                    "END IF; "
                    "ALTER TABLE daily_health_entries "
                    "DROP COLUMN reported_thirst_score_0_10, "
                    "DROP COLUMN reported_dryness_score_0_10; "
                    "END IF; END $$;"
                )
            )
            await connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_consents_active_user_version "
                    "ON consents (user_id, version) WHERE revoked_at IS NULL"
                )
            )
            await connection.execute(
                text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conrelid = 'analyses'::regclass "
                    "AND conname = 'uq_analyses_id_user') THEN "
                    "ALTER TABLE analyses ADD CONSTRAINT uq_analyses_id_user "
                    "UNIQUE (id, user_id); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint "
                    "WHERE conrelid = 'annotation_tasks'::regclass "
                    "AND conname = 'fk_annotation_analysis_owner') THEN "
                    "ALTER TABLE annotation_tasks ADD CONSTRAINT fk_annotation_analysis_owner "
                    "FOREIGN KEY (analysis_id, user_id) REFERENCES analyses (id, user_id); "
                    "END IF; END $$;"
                )
            )


async def close_database() -> None:
    await engine.dispose()
