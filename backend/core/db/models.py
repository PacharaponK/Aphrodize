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
    Integer,
    String,
    UniqueConstraint,
    func,
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
    id: Mapped[uuid.UUID] = uuid_pk()
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
            "sleep_duration_minutes >= 0 AND sleep_duration_minutes <= 540",
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


class DailyHealthProfile(Base):
    """Consent-gated, user-reported context for personalizing wellness guidance."""

    __tablename__ = "daily_health_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    smoking_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DailyHealthAgeBand(Base):
    """Optional, consent-gated age band for age-aware sleep guidance; no birth date stored."""

    __tablename__ = "daily_health_age_bands"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


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
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    target_date: Mapped[date] = mapped_column(Date)
    reported_energy_level_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_thirst_level_0_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
