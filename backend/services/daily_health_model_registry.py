"""Safe loading helpers for explicitly approved daily-health model candidates."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.consents import MODEL_TRAINING_CONSENT_VERSION, MODEL_TRAINING_CONSENT_VERSIONS
from backend.core.db.models import DailyHealthModelDeployment, DailyHealthModelVersion
from backend.services.daily_health_training import (
    ARTIFACT_ROOT,
    ENERGY_TARGET_NAMES,
    FEATURE_AVAILABILITY_POLICY,
    FEATURE_NAMES,
    MODEL_FAMILY,
    TARGET_NAMES,
)

VERSION_ID_PATTERN = re.compile(r"^daily-health-next-day-[0-9a-f]{16}$")
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MIN_TRAINING_RECORDS = 100
MIN_TRAINING_PARTICIPANTS = 5


def _safe_artifact_root(artifact_root: Path) -> Path:
    if artifact_root == ARTIFACT_ROOT:
        repository_root = Path(__file__).resolve().parents[2]
        expected_root = (
            repository_root / "models/time-series/non-linear-model/artifacts/user-candidates"
        )
        current = repository_root
        for component in expected_root.relative_to(repository_root).parts:
            current = current / component
            if current.is_symlink():
                raise DailyHealthCandidateUnavailable(
                    "Candidate artifact root cannot contain symlinks."
                )
        root = expected_root.resolve()
        try:
            root.relative_to(repository_root)
        except ValueError as error:
            raise DailyHealthCandidateUnavailable(
                "Candidate artifact root is outside the repository."
            ) from error
        return root
    return artifact_root.resolve()


class DailyHealthCandidateUnavailable(RuntimeError):
    """Candidate is absent, mismatched, or unsafe to load for serving."""


def load_approved_candidate_bundle(
    version: DailyHealthModelVersion,
    *,
    artifact_root: Path = ARTIFACT_ROOT,
) -> dict[str, Any]:
    """Load only an intact candidate artifact from its exact generated directory."""
    if version.status != "candidate":
        raise DailyHealthCandidateUnavailable("Only a review-approved candidate can be deployed.")
    if not VERSION_ID_PATTERN.fullmatch(version.version_id):
        raise DailyHealthCandidateUnavailable("Candidate version identifier is invalid.")
    if not FINGERPRINT_PATTERN.fullmatch(version.dataset_fingerprint):
        raise DailyHealthCandidateUnavailable("Candidate dataset fingerprint is invalid.")
    if version.model_family != MODEL_FAMILY:
        raise DailyHealthCandidateUnavailable("Candidate model family is unsupported.")
    if (
        version.training_records < MIN_TRAINING_RECORDS
        or version.participant_count < MIN_TRAINING_PARTICIPANTS
    ):
        raise DailyHealthCandidateUnavailable("Candidate training cohort is below policy minimums.")

    root = _safe_artifact_root(artifact_root)
    expected_uri = (
        Path("models")
        / "time-series"
        / "non-linear-model"
        / "artifacts"
        / "user-candidates"
        / version.version_id
        / "model.joblib"
    ).as_posix()
    if version.artifact_uri != expected_uri:
        raise DailyHealthCandidateUnavailable(
            "Candidate artifact path is outside the approved layout."
        )

    candidate_dir = root / version.version_id
    if candidate_dir.is_symlink():
        raise DailyHealthCandidateUnavailable("Candidate artifact directory cannot be a symlink.")
    try:
        resolved_dir = candidate_dir.resolve(strict=True)
        resolved_dir.relative_to(root)
    except (OSError, ValueError) as error:
        raise DailyHealthCandidateUnavailable(
            "Candidate artifact directory is unavailable."
        ) from error
    if resolved_dir.parent != root:
        raise DailyHealthCandidateUnavailable("Candidate artifact directory is not a direct child.")

    artifact_path = resolved_dir / "model.joblib"
    manifest_path = resolved_dir / "manifest.json"
    if artifact_path.is_symlink() or manifest_path.is_symlink():
        raise DailyHealthCandidateUnavailable("Candidate files cannot be symlinks.")
    if not artifact_path.is_file() or not manifest_path.is_file():
        raise DailyHealthCandidateUnavailable("Candidate artifact or manifest is missing.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError) as error:
        raise DailyHealthCandidateUnavailable(
            "Candidate manifest or artifact cannot be read."
        ) from error

    target_names = manifest.get("targets")
    if target_names not in (TARGET_NAMES, ENERGY_TARGET_NAMES):
        raise DailyHealthCandidateUnavailable("Candidate targets are unsupported.")
    expected_manifest = {
        "version_id": version.version_id,
        "model_family": MODEL_FAMILY,
        "prediction_horizon_days": 1,
        "features": FEATURE_NAMES,
        "targets": target_names,
        "training_records": version.training_records,
        "participant_count": version.participant_count,
        "dataset_fingerprint": version.dataset_fingerprint,
        "data_policy": "active_opt_in_and_user_reported_numeric_outcomes_only",
        "synthetic_data_included": False,
        "predictions_used_as_labels": False,
        "feature_availability_policy": FEATURE_AVAILABILITY_POLICY,
        "training_consent_versions": (
            [MODEL_TRAINING_CONSENT_VERSION] if target_names == ENERGY_TARGET_NAMES
            else list(MODEL_TRAINING_CONSENT_VERSIONS)
        ),
    }
    if any(manifest.get(key) != value for key, value in expected_manifest.items()):
        raise DailyHealthCandidateUnavailable(
            "Candidate manifest does not match its registry record."
        )
    if manifest.get("artifact_sha256") != artifact_digest:
        raise DailyHealthCandidateUnavailable(
            "Candidate artifact checksum does not match its manifest."
        )
    if version.metrics != manifest.get("metrics"):
        raise DailyHealthCandidateUnavailable("Candidate metrics do not match the stored manifest.")
    if not isinstance(version.metrics, dict) or not {"validation", "test"}.issubset(
        version.metrics
    ):
        raise DailyHealthCandidateUnavailable(
            "Candidate has no validation and holdout test metrics."
        )
    # Every target must beat a train-only baseline in both independent views.
    for target in target_names:
        for split, baseline in (
            ("test", "test_mean_baseline"),
            ("temporal_test", "temporal_mean_baseline"),
        ):
            try:
                error = version.metrics[split][target]["mae"]
                baseline_error = version.metrics[baseline][target]["mae"]
            except (KeyError, TypeError) as exc:
                raise DailyHealthCandidateUnavailable(
                    f"Candidate requires participant and temporal baseline metrics for {target}."
                ) from exc
            if (type(error) not in (int, float) or type(baseline_error) not in (int, float)
                    or not math.isfinite(error) or not math.isfinite(baseline_error)
                    or not 0 <= error < baseline_error):
                raise DailyHealthCandidateUnavailable(
                    f"Candidate does not outperform its observed-outcome baseline for {target}."
                )

    try:
        estimator = joblib.load(artifact_path)
    except Exception as error:
        raise DailyHealthCandidateUnavailable(
            "Candidate model artifact could not be loaded."
        ) from error
    if getattr(estimator, "n_features_in_", None) != len(FEATURE_NAMES):
        raise DailyHealthCandidateUnavailable("Candidate feature shape is unsupported.")
    if getattr(estimator, "n_outputs_", None) != len(target_names):
        raise DailyHealthCandidateUnavailable("Candidate target shape is unsupported.")

    return {
        "model": estimator,
        "metadata": {
            "model_id": version.version_id,
            "model_family": MODEL_FAMILY,
            "features": FEATURE_NAMES,
            "targets": target_names,
            "prediction_horizon_days": 1,
            "data_policy": "active_opt_in_and_user_reported_numeric_outcomes_only",
            "holdout": {"metrics": version.metrics.get("test", {})},
            "validation": version.metrics.get("validation", {}),
        },
    }


async def get_serving_daily_health_bundle(session: AsyncSession) -> dict[str, Any] | None:
    """Return None for the source-controlled baseline; otherwise load the active candidate."""
    deployment = await session.get(DailyHealthModelDeployment, "daily_health")
    if deployment is None or deployment.active_version_id is None:
        return None
    version = await session.get(DailyHealthModelVersion, deployment.active_version_id)
    if version is None:
        raise DailyHealthCandidateUnavailable("Active model version is missing from the registry.")
    return load_approved_candidate_bundle(version)


def purge_generated_candidate_artifacts(
    version_ids: list[str], *, artifact_root: Path = ARTIFACT_ROOT
) -> int:
    """Remove only known direct files for generated candidate IDs; never recurse or follow links."""
    root = _safe_artifact_root(artifact_root)
    purge_plan: list[tuple[Path, list[Path]]] = []
    for version_id in sorted(set(version_ids)):
        if not VERSION_ID_PATTERN.fullmatch(version_id):
            raise DailyHealthCandidateUnavailable("Refusing to purge an unrecognized candidate ID.")
        candidate_dir = root / version_id
        if candidate_dir.is_symlink():
            raise DailyHealthCandidateUnavailable(
                "Refusing to purge a symlinked candidate directory."
            )
        if not candidate_dir.exists():
            continue
        try:
            resolved_dir = candidate_dir.resolve(strict=True)
            resolved_dir.relative_to(root)
        except (OSError, ValueError) as error:
            raise DailyHealthCandidateUnavailable("Candidate artifact path is unsafe.") from error
        if resolved_dir.parent != root:
            raise DailyHealthCandidateUnavailable("Candidate directory is not a direct child.")

        allowed_names = {"model.joblib", "manifest.json"}
        unexpected_names = {entry.name for entry in resolved_dir.iterdir()} - allowed_names
        if unexpected_names:
            raise DailyHealthCandidateUnavailable(
                "Candidate directory contains unrecognized files; manual review is required."
            )
        manifest_path = resolved_dir / "manifest.json"
        if manifest_path.is_symlink():
            raise DailyHealthCandidateUnavailable("Refusing to purge a symlinked manifest.")
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise DailyHealthCandidateUnavailable(
                    "Candidate manifest is unreadable."
                ) from error
            if manifest.get("version_id") != version_id:
                raise DailyHealthCandidateUnavailable(
                    "Candidate manifest version does not match its path."
                )

        files: list[Path] = []
        for name in ("model.joblib", "manifest.json"):
            path = resolved_dir / name
            if path.is_symlink():
                raise DailyHealthCandidateUnavailable(
                    "Refusing to purge a symlinked candidate file."
                )
            if path.exists():
                if not path.is_file():
                    raise DailyHealthCandidateUnavailable("Candidate output is not a regular file.")
                files.append(path)
        purge_plan.append((resolved_dir, files))

    deleted_count = 0
    for candidate_dir, files in purge_plan:
        for path in files:
            path.unlink()
            deleted_count += 1
        candidate_dir.rmdir()
    return deleted_count
