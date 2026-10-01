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
        product_columns = await connection.run_sync(
            lambda sync_connection: {
                column["name"] for column in inspect(sync_connection).get_columns("products")
            }
        ) or set()
        product_additions = {
            "variant": "VARCHAR(120) NOT NULL DEFAULT ''",
            "market": "VARCHAR(8)",
            "price_source_url": "VARCHAR(1000)",
            "application_regions": "JSON NOT NULL DEFAULT '[]'",
            "price_satang": "INTEGER",
            "price_checked_at": "TIMESTAMP WITH TIME ZONE",
            "ingredients_label": "TEXT NOT NULL DEFAULT ''",
            "ingredients_inci": "JSON NOT NULL DEFAULT '[]'",
            "warnings_label": "TEXT NOT NULL DEFAULT ''",
            "target_skin_types": "JSON NOT NULL DEFAULT '[]'",
            "concerns": "JSON NOT NULL DEFAULT '[]'",
            "source_url": "VARCHAR(1000)",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'draft'",
            "reviewed_at": "TIMESTAMP WITH TIME ZONE",
            "updated_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "spf": "INTEGER",
            "broad_spectrum": "BOOLEAN NOT NULL DEFAULT false",
            "water_resistant_minutes": "INTEGER",
        }
        for name, definition in product_additions.items():
            if name not in product_columns:
                await connection.execute(
                    text(f"ALTER TABLE products ADD COLUMN {name} {definition}")
                )
        if connection.dialect.name == "postgresql" and "price_thb" in product_columns:
            # Preserve legacy catalog values; no product becomes published without review.
            await connection.execute(
                text(
                    "UPDATE products SET price_satang = ROUND(price_thb * 100)::integer "
                    "WHERE price_satang IS NULL AND price_thb IS NOT NULL"
                )
            )
            await connection.execute(
                text(
                    "UPDATE products SET ingredients_label = ingredients_text "
                    "WHERE ingredients_label = '' AND ingredients_text IS NOT NULL"
                )
            )
            await connection.execute(
                text(
                    "UPDATE products SET source_url = product_url "
                    "WHERE source_url IS NULL AND product_url IS NOT NULL"
                )
            )
            for legacy_column in ("price_thb", "ingredients_text", "is_active"):
                await connection.execute(
                    text(f"ALTER TABLE products ALTER COLUMN {legacy_column} DROP NOT NULL")
                )
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
            if "height_cm" not in profile_columns:
                await connection.execute(
                    text("ALTER TABLE daily_health_profiles ADD COLUMN height_cm FLOAT")
                )
        if connection.dialect.name == "postgresql":
            # Keep legacy tables intact during startup; data removal requires an
            # explicit, separately reviewed migration rather than an implicit DDL step.
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
                text("ALTER TABLE daily_health_profiles ADD COLUMN IF NOT EXISTS weight_kg FLOAT")
            )
            await connection.execute(
                text("ALTER TABLE daily_health_profiles ADD COLUMN IF NOT EXISTS height_cm FLOAT")
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
                    "WHERE conname = 'ck_daily_health_profile_height' "
                    "AND conrelid = 'daily_health_profiles'::regclass) THEN "
                    "ALTER TABLE daily_health_profiles "
                    "ADD CONSTRAINT ck_daily_health_profile_height CHECK "
                    "(height_cm IS NULL OR (height_cm >= 30 AND height_cm <= 300)); "
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
            # These are user-reported signals used by the recommendation rules.  Keep
            # existing values and add the fields for databases created by older builds.
            await connection.execute(
                text(
                    "ALTER TABLE daily_health_entries "
                    "ADD COLUMN IF NOT EXISTS reported_thirst_score_0_10 FLOAT, "
                    "ADD COLUMN IF NOT EXISTS reported_dryness_score_0_10 FLOAT"
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
