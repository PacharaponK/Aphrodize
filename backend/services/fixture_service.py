import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import AwareDatetime, TypeAdapter
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.auth import SignupRequest
from backend.api.schemas.consent import WellnessProfileUpsert
from backend.api.schemas.daily_health import DailyHealthEntryUpsert
from backend.api.schemas.product import ProductInput
from backend.api.v1.routes.auth import signup
from backend.api.v1.routes.products import require_publishable
from backend.core.db.models import (
    Account,
    Consent,
    DailyHealthDatasetRecord,
    DailyHealthEntry,
    Product,
    UserProfile,
)


def products_from_fixture(path: Path) -> list[Product]:
    """Validate the entire source snapshot before writing any catalog rows."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("products"), list):
        raise ValueError("Fixture must contain a products list")
    if not data["products"]:
        raise ValueError("Product fixture cannot be empty")
    reviewed_at = TypeAdapter(AwareDatetime).validate_python(data.get("reviewed_at"))
    products = []
    source_urls = set()
    for row in data["products"]:
        payload = ProductInput.model_validate(row)
        if not payload.ingredients_label:
            payload.ingredients_label = ", ".join(payload.ingredients_inci)
        product = Product(**payload.model_dump(), status="published", reviewed_at=reviewed_at)
        require_publishable(product)
        if product.source_url in source_urls:
            raise ValueError("Product fixture contains duplicate source URLs")
        source_urls.add(product.source_url)
        if product.price_satang is not None:
            product.price_checked_at = reviewed_at
        products.append(product)
    return products


async def load_products(path: Path, session: AsyncSession) -> int:
    products = products_from_fixture(path)
    inserted = 0
    enriched = False
    for product in products:
        existing = await session.scalar(select(Product).where(
            Product.source_url == product.source_url,
        ).limit(1))
        if existing is None:
            session.add(product)
            inserted += 1
        elif (
            existing.status == "published" and existing.reviewed_at is not None
            and [v.strip().casefold() for v in existing.ingredients_inci]
            == [v.strip().casefold() for v in product.ingredients_inci]
        ):
            # Fill missing market/price provenance only for the identical reviewed formula.
            # Preserve archived rows, edited labels and any price already entered by an admin.
            if existing.market is None and product.market is not None:
                existing.market = product.market
                enriched = True
            if (
                existing.price_satang is None and existing.price_source_url is None
                and product.price_satang is not None and product.price_source_url
            ):
                existing.price_satang = product.price_satang
                existing.price_source_url = product.price_source_url
                existing.price_checked_at = product.price_checked_at
                enriched = True
    if inserted or enriched:
        await session.commit()
    return inserted


async def load_users(path: Path, session: AsyncSession) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("users", []), list):
        raise ValueError("Fixture must contain a users list")

    for row in data.get("users", []):
        user = SignupRequest.model_validate(row)
        profile = (
            WellnessProfileUpsert.model_validate(row["profile"])
            if "profile" in row else None
        )
        account = await session.scalar(select(Account).where(Account.email == user.email))
        user_id = account.user_id if account else (await signup(user, session)).user_id
        changed = False
        if profile is not None:
            existing = await session.get(UserProfile, user_id)
            if existing is None:
                session.add(UserProfile(user_id=user_id, **profile.profile_values()))
                changed = True

        entries = row.get("daily_entries", [])
        if entries:
            consent = await session.scalar(
                select(Consent.id).where(
                    Consent.user_id == user_id,
                    Consent.version == "daily-health-v1",
                    Consent.revoked_at.is_(None),
                ).limit(1)
            )
            if consent is None:
                session.add(Consent(user_id=user_id, version="daily-health-v1"))
                changed = True
            for entry in entries:
                DailyHealthEntryUpsert.model_validate(entry)
                if entry["data_source"] != "fixture":
                    raise ValueError("Fixture daily entries must use data_source=fixture")
                score = round(min(100.0, entry["sleep_duration_minutes"] / 540 * 100), 1)
                if entry["sleep_score_0_100"] != score:
                    raise ValueError("Fixture sleep score does not match its duration")
                statement = insert(DailyHealthEntry).values(user_id=user_id, **entry)
                inserted_id = await session.scalar(
                    statement.on_conflict_do_nothing(
                        index_elements=[DailyHealthEntry.user_id, DailyHealthEntry.local_date]
                    ).returning(DailyHealthEntry.id)
                )
                changed = changed or inserted_id is not None
        if changed:
            await session.commit()

    dataset = data.get("daily_health_dataset")
    if dataset is not None:
        await _load_daily_health_dataset(dataset, session)


async def _load_daily_health_dataset(dataset: Any, session: AsyncSession) -> None:
    """Load raw historical tracker rows without converting them into app scores or labels."""
    if not isinstance(dataset, dict) or not isinstance(dataset.get("records"), list):
        raise ValueError("Fixture daily_health_dataset must contain a records list")

    dataset_name = dataset.get("source_dataset_name")
    records = dataset["records"]
    if not isinstance(dataset_name, str) or not dataset_name.strip():
        raise ValueError("Fixture daily_health_dataset requires source_dataset_name")
    if len(dataset_name) > 255 or not records:
        raise ValueError("Fixture daily_health_dataset name is too long or records are empty")

    fingerprint_payload = json.dumps(
        dataset, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_payload).hexdigest()
    participant_aliases: dict[str, str] = {}
    normalized_records = []
    required_fields = {
        "local_date",
        "data_origin",
        "source_user_id",
        "source_local_date_raw",
        "source_sleep_duration_hours_raw",
        "source_sleep_duration_mins_raw",
        "skin_dryness_level",
        "skin_feeling_status",
        "outdoor_minutes",
    }
    allowed_fields = (required_fields, required_fields | {"water_intake_ml"})

    for row_number, record in enumerate(records, start=1):
        if not isinstance(record, dict) or set(record) not in allowed_fields:
            raise ValueError(f"Fixture daily-health dataset row {row_number} has invalid fields")
        if record["data_origin"] not in {"real_user_tracker_xlsx", "tester"}:
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has unknown provenance"
            )
        if "water_intake_ml" in record and (
            not isinstance(record["water_intake_ml"], int)
            or isinstance(record["water_intake_ml"], bool)
            or not 0 <= record["water_intake_ml"] <= 20_000
        ):
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has invalid water intake"
            )
        try:
            local_date = date.fromisoformat(str(record["local_date"]))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has an invalid local_date"
            ) from error

        raw_date = record["source_local_date_raw"]
        try:
            raw_day, raw_month, _raw_year = (int(part) for part in raw_date.split("/"))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has an invalid source date"
            ) from error
        if (raw_day, raw_month) != (local_date.day, local_date.month):
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has mismatched source date"
            )

        sleep_hours = record["source_sleep_duration_hours_raw"]
        sleep_minutes = record["source_sleep_duration_mins_raw"]
        if (sleep_hours == "no recorded") != (sleep_minutes == "no recorded"):
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} must mark both sleep fields"
            )
        if sleep_hours != "no recorded" and (
            not isinstance(sleep_hours, int)
            or isinstance(sleep_hours, bool)
            or not isinstance(sleep_minutes, int)
            or isinstance(sleep_minutes, bool)
            or not 0 <= sleep_hours <= 10
            or not 0 <= sleep_minutes <= 59
        ):
            raise ValueError(
                f"Fixture daily-health dataset row {row_number} has invalid raw sleep duration"
            )

        source_user_id = str(record["source_user_id"])
        if not source_user_id:
            raise ValueError(f"Fixture daily-health dataset row {row_number} has no source user id")
        participant_key = participant_aliases.setdefault(
            source_user_id,
            f"participant_{len(participant_aliases) + 1:04d}",
        )
        normalized_records.append((row_number, local_date, participant_key, record))

    changed = False
    for row_number, local_date, participant_key, record in normalized_records:
        payload = {
            **record,
            "local_date": local_date.isoformat(),
            "source_user_id": participant_key,
        }
        statement = insert(DailyHealthDatasetRecord).values(
            dataset_fingerprint=fingerprint,
            source_dataset_name=dataset_name.strip(),
            source_row_number=row_number,
            participant_key=participant_key,
            local_date=local_date,
            data_source="observed",
            generation_rule_version=None,
            training_eligible=False,
            training_exclusion_reason="imported_labels_not_numeric_ground_truth",
            record_payload=payload,
        )
        inserted_id = await session.scalar(
            statement.on_conflict_do_nothing(
                index_elements=[
                    DailyHealthDatasetRecord.dataset_fingerprint,
                    DailyHealthDatasetRecord.source_row_number,
                ]
            ).returning(DailyHealthDatasetRecord.id)
        )
        if inserted_id is not None:
            changed = True
    if changed:
        await session.commit()
