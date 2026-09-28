import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db.base import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class AnalysisStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    rejected = "rejected"
    failed = "failed"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'deleted')", name="ck_users_status"
        ),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Account(Base):
    """Credentials and profile data kept separate from clinical/workflow user data."""

    __tablename__ = "accounts"
    __table_args__ = (
        # Application code normalizes email on input. This unique expression index also
        # protects the invariant when data is inserted outside the API.
        Index("uq_accounts_email_normalized", func.lower(text("email")), unique=True),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AccountRole(Base):
    """Small RBAC join table; roles are data, not hard-coded account flags."""

    __tablename__ = "account_roles"
    __table_args__ = (
        UniqueConstraint("account_id", "role", name="uq_account_roles_account_role"),
        CheckConstraint(
            "role IN ('member', 'admin', 'support')", name="ck_account_roles_role"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32), default="member", server_default="member")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    granted_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )


class AuthSession(Base):
    """Per-device session. Only a hash of the refresh credential is persisted."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_account_active", "account_id", "expires_at", "revoked_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuthToken(Base):
    """Short-lived, single-use token for email verification or password reset."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('email_verification', 'password_reset')",
            name="ck_auth_tokens_purpose",
        ),
        Index("ix_auth_tokens_account_purpose_active", "account_id", "purpose", "expires_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoginAudit(Base):
    """Minimal security audit. Do not store raw IP addresses or submitted passwords."""

    __tablename__ = "login_audit"
    __table_args__ = (Index("ix_login_audit_account_created", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email_hash: Mapped[str] = mapped_column(String(128), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    version: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Questionnaire(Base):
    __tablename__ = "questionnaires"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    answers: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    """Admin-reviewed catalog data; intentionally independent of user records."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_satang IS NULL OR price_satang >= 0", name="ck_product_price"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_product_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    brand: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    variant: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(64))
    price_satang: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingredients_label: Mapped[str] = mapped_column(Text, default="")
    ingredients_inci: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings_label: Mapped[str] = mapped_column(Text, default="")
    target_skin_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    concerns: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyLifestyleObservation(Base):
    """One day of standardized wrinkle scoring and self-reported lifestyle data."""

    __tablename__ = "daily_lifestyle_observations"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_lifestyle_observation_user_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    wrinkle_score: Mapped[float] = mapped_column(Float)
    sleep_hours: Mapped[float] = mapped_column(Float)
    water_intake_ml: Mapped[float] = mapped_column(Float)
    outdoor_minutes: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyHealthEntry(Base):
    """User-reported daily tracker inputs and separate, non-label model outputs."""

    __tablename__ = "daily_health_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_daily_health_user_date"),
        CheckConstraint(
            "sleep_duration_minutes >= 0 AND sleep_duration_minutes <= 600",
            name="ck_daily_health_sleep_duration",
        ),
        CheckConstraint(
            "water_intake_ml >= 0 AND water_intake_ml <= 20000",
            name="ck_daily_health_water_intake",
        ),
        CheckConstraint(
            "outdoor_exposure_choice >= 1 AND outdoor_exposure_choice <= 4",
            name="ck_daily_health_outdoor_choice",
        ),
        CheckConstraint(
            "sleep_score_0_100 >= 0 AND sleep_score_0_100 <= 100",
            name="ck_daily_health_sleep_score",
        ),
        CheckConstraint(
            "predicted_thirst_score_0_10 IS NULL OR "
            "(predicted_thirst_score_0_10 >= 0 AND predicted_thirst_score_0_10 <= 10)",
            name="ck_daily_health_predicted_thirst",
        ),
        CheckConstraint(
            "predicted_dryness_score_0_10 IS NULL OR "
            "(predicted_dryness_score_0_10 >= 0 AND predicted_dryness_score_0_10 <= 10)",
            name="ck_daily_health_predicted_dryness",
        ),
        CheckConstraint(
            "reported_thirst_score_0_10 IS NULL OR "
            "(reported_thirst_score_0_10 >= 0 AND reported_thirst_score_0_10 <= 10)",
            name="ck_daily_health_reported_thirst",
        ),
        CheckConstraint(
            "reported_dryness_score_0_10 IS NULL OR "
            "(reported_dryness_score_0_10 >= 0 AND reported_dryness_score_0_10 <= 10)",
            name="ck_daily_health_reported_dryness",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Bangkok")
    sleep_duration_minutes: Mapped[int] = mapped_column(Integer)
    water_intake_ml: Mapped[int] = mapped_column(Integer)
    outdoor_exposure_choice: Mapped[int] = mapped_column(Integer)
    sleep_score_0_100: Mapped[float] = mapped_column(Float)
    sleep_score_method: Mapped[str] = mapped_column(String(128))
    predicted_thirst_score_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_dryness_score_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    prediction_status: Mapped[str] = mapped_column(String(32), default="not_run")
    prediction_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="user_reported")
    # These remain NULL until the user supplies real observed outcomes; predictions are not labels.
    reported_thirst_score_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_dryness_score_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def training_eligible(self) -> bool:
        return (
            self.reported_thirst_score_0_10 is not None
            and self.reported_dryness_score_0_10 is not None
        )


class DailyHealthDatasetRecord(Base):
    """Imported historical dataset row, retained with provenance and excluded by default."""

    __tablename__ = "daily_health_dataset_records"
    __table_args__ = (
        UniqueConstraint(
            "dataset_fingerprint",
            "source_row_number",
            name="uq_daily_health_dataset_fingerprint_row",
        ),
        CheckConstraint(
            "data_source IN ('observed', 'synthetic', 'unknown')",
            name="ck_daily_health_dataset_data_source",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    source_dataset_name: Mapped[str] = mapped_column(String(255))
    source_row_number: Mapped[int] = mapped_column(Integer)
    participant_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    local_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_source: Mapped[str] = mapped_column(String(16))
    generation_rule_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    training_eligible: Mapped[bool] = mapped_column(default=False)
    training_exclusion_reason: Mapped[str] = mapped_column(String(128))
    record_payload: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DailyHealthProfile(Base):
    """Consent-gated, user-reported context for personalizing wellness guidance."""

    __tablename__ = "daily_health_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    smoking_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyHealthAgeBand(Base):
    """Optional, consent-gated age band for age-aware sleep guidance; no birth date stored."""

    __tablename__ = "daily_health_age_bands"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age_band: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyHealthMenstrualCheckIn(Base):
    """Optional, user-reported menstruation status for a single local date."""

    __tablename__ = "daily_health_menstrual_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_menstrual_checkin_user_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    currently_menstruating: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyHealthOutcome(Base):
    """User-reported next-day outcomes kept separate from model predictions."""

    __tablename__ = "daily_health_outcomes"
    __table_args__ = (
        UniqueConstraint("user_id", "target_date", name="uq_daily_health_outcome_user_date"),
        CheckConstraint(
            "reported_energy_level_0_10 IS NULL OR "
            "(reported_energy_level_0_10 >= 0 AND reported_energy_level_0_10 <= 10)",
            name="ck_daily_health_reported_energy",
        ),
        CheckConstraint(
            "reported_thirst_level_0_10 IS NULL OR "
            "(reported_thirst_level_0_10 >= 0 AND reported_thirst_level_0_10 <= 10)",
            name="ck_daily_health_reported_thirst_level",
        ),
        CheckConstraint(
            "reported_dryness_level_0_10 IS NULL OR "
            "(reported_dryness_level_0_10 >= 0 AND reported_dryness_level_0_10 <= 10)",
            name="ck_daily_health_reported_dryness_level",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_date: Mapped[date] = mapped_column(Date)
    reported_energy_level_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_thirst_level_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_dryness_level_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyHealthModelVersion(Base):
    """Immutable candidate registry for consented, user-reported daily-health models."""

    __tablename__ = "daily_health_model_versions"
    __table_args__ = (
        UniqueConstraint("dataset_fingerprint", name="uq_daily_health_model_dataset"),
    )

    version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    model_family: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="training")
    dataset_fingerprint: Mapped[str] = mapped_column(String(64))
    training_records: Mapped[int] = mapped_column(Integer)
    participant_count: Mapped[int] = mapped_column(Integer)
    artifact_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DailyHealthModelDeployment(Base):
    """Explicitly approved model currently serving daily-health predictions."""

    __tablename__ = "daily_health_model_deployments"

    deployment_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    active_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("daily_health_model_versions.version_id"), nullable=True
    )
    previous_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("daily_health_model_versions.version_id"), nullable=True
    )
    approval_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyHealthModelDeploymentEvent(Base):
    """Append-only audit record for explicit model promotion and rollback actions."""

    __tablename__ = "daily_health_model_deployment_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    action: Mapped[str] = mapped_column(String(24))
    version_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.queued
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_type: Mapped[str] = mapped_column(String(128))
    image_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    model_family: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(128))
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"
    __table_args__ = (UniqueConstraint("analysis_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    label_studio_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrainingRun(Base):
    __tablename__ = "training_runs"
    id: Mapped[uuid.UUID] = uuid_pk()
    model_family: Mapped[str] = mapped_column(String(64))
    dataset_uri: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    mlflow_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InferenceRun(Base):
    """Generic model request for approved time-series and non-time-series model deployments."""

    __tablename__ = "inference_runs"
    id: Mapped[uuid.UUID] = uuid_pk()
    model_family: Mapped[str] = mapped_column(String(64))
    model_uri: Mapped[str] = mapped_column(String(512))
    input_data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
