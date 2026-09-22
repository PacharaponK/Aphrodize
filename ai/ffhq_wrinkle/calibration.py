"""Held-out target-user validation and confidence-policy calibration."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .confidence import ConfidencePolicy

CALIBRATION_METHOD = "mean-binary-decision-margin"
CALIBRATION_REPORT_VERSION = "wrinkle-confidence-calibration-v1"
CALIBRATION_POLICY_VERSION = "wrinkle-confidence-gate-v2"
VALIDATION_MANIFEST_VERSION = "aphrodize-target-user-validation-v1"


@dataclass(frozen=True)
class ValidationRecord:
    sample_id: str
    subject_id: str
    confidence: float
    dice: float
    quality_passed: bool


@dataclass(frozen=True)
class CalibrationRequirements:
    minimum_samples: int = 100
    minimum_subjects: int = 50
    minimum_accepted: int = 30
    target_precision: float = 0.90
    dice_target: float = 0.60
    wilson_z: float = 1.96

    def validate(self) -> None:
        if min(self.minimum_samples, self.minimum_subjects, self.minimum_accepted) < 1:
            raise ValueError("minimum sample, subject, and accepted counts must be positive")
        if not 0 < self.target_precision <= 1 or not 0 <= self.dice_target <= 1:
            raise ValueError("precision and Dice targets must be within [0, 1]")
        if self.wilson_z <= 0:
            raise ValueError("wilson_z must be positive")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError("quality_passed must be true or false")
    return normalized == "true"


def load_validation_records(path: str | Path) -> list[ValidationRecord]:
    required = {"sample_id", "subject_id", "confidence", "dice", "quality_passed"}
    records: list[ValidationRecord] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ValueError(f"validation CSV columns must be exactly {sorted(required)}")
        for row_number, row in enumerate(reader, start=2):
            try:
                record = ValidationRecord(
                    sample_id=row["sample_id"].strip(),
                    subject_id=row["subject_id"].strip(),
                    confidence=float(row["confidence"]),
                    dice=float(row["dice"]),
                    quality_passed=_parse_bool(row["quality_passed"]),
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid validation record at CSV row {row_number}: {error}") from error
            if not record.sample_id or not record.subject_id:
                raise ValueError(f"sample_id and subject_id are required at CSV row {row_number}")
            if not math.isfinite(record.confidence) or not 0 <= record.confidence <= 1:
                raise ValueError(f"confidence must be finite and within [0, 1] at row {row_number}")
            if not math.isfinite(record.dice) or not 0 <= record.dice <= 1:
                raise ValueError(f"dice must be finite and within [0, 1] at row {row_number}")
            records.append(record)
    sample_ids = [record.sample_id for record in records]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("validation sample_id values must be unique")
    return records


def validate_manifest(
    manifest: dict[str, object], records_path: str | Path, records: list[ValidationRecord]
) -> None:
    required = {
        "manifest_version",
        "dataset_id",
        "dataset_version",
        "purpose",
        "source_kind",
        "consent_scope",
        "identity_split_method",
        "independent_from_training",
        "independent_from_official_test",
        "official_test_overlap_count",
        "sample_count",
        "subject_count",
        "capture_protocol",
        "annotation_guideline",
        "records_sha256",
        "model_architecture",
        "checkpoint_sha256",
        "prediction_version",
        "preprocessing_version",
        "threshold_version",
        "confidence_method",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"validation manifest is missing fields: {missing}")
    if manifest["manifest_version"] != VALIDATION_MANIFEST_VERSION:
        raise ValueError("unsupported validation manifest version")
    if manifest["purpose"] != "confidence_calibration" or manifest["source_kind"] != "target_user":
        raise ValueError("calibration requires a target-user confidence-calibration dataset")
    if manifest["confidence_method"] != CALIBRATION_METHOD:
        raise ValueError("validation confidence method does not match the calibration method")
    if manifest["independent_from_training"] is not True:
        raise ValueError("validation dataset must be independent from training data")
    if manifest["independent_from_official_test"] is not True:
        raise ValueError("validation dataset must be independent from the official test set")
    if manifest["official_test_overlap_count"] != 0:
        raise ValueError("validation dataset must have zero official-test overlap")
    consent_scope = manifest["consent_scope"]
    if not isinstance(consent_scope, list) or not all(
        isinstance(scope, str) for scope in consent_scope
    ):
        raise ValueError("consent_scope must be a list of strings")
    if "validation" not in consent_scope:
        raise ValueError("consent_scope must explicitly include validation")
    if int(manifest["sample_count"]) != len(records):
        raise ValueError("manifest sample_count does not match validation CSV")
    subjects = {record.subject_id for record in records}
    if int(manifest["subject_count"]) != len(subjects):
        raise ValueError("manifest subject_count does not match validation CSV")
    if manifest["records_sha256"] != sha256_file(records_path):
        raise ValueError("validation CSV checksum does not match manifest")
    for field in (
        "dataset_id",
        "dataset_version",
        "identity_split_method",
        "capture_protocol",
        "annotation_guideline",
        "model_architecture",
        "checkpoint_sha256",
        "prediction_version",
        "preprocessing_version",
        "threshold_version",
    ):
        if not str(manifest[field]).strip():
            raise ValueError(f"validation manifest field {field} must not be empty")


def load_and_validate_dataset(
    records_path: str | Path, manifest_path: str | Path
) -> tuple[list[ValidationRecord], dict[str, object]]:
    records = load_validation_records(records_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("validation manifest must contain a JSON object")
    validate_manifest(manifest, records_path, records)
    manifest = {**manifest, "manifest_sha256": sha256_file(manifest_path)}
    return records, manifest


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0 or not 0 <= successes <= total:
        return 0.0
    proportion = successes / total
    z2 = z * z
    center = proportion + z2 / (2 * total)
    spread = z * math.sqrt((proportion * (1 - proportion) + z2 / (4 * total)) / total)
    return (center - spread) / (1 + z2 / total)


def calibrate_confidence(
    records: list[ValidationRecord],
    manifest: dict[str, object],
    calibration_version: str,
    requirements: CalibrationRequirements = CalibrationRequirements(),
) -> tuple[dict[str, object], dict[str, object]]:
    """Select the widest-coverage threshold satisfying a Wilson precision gate."""

    requirements.validate()
    if not calibration_version.strip():
        raise ValueError("calibration_version must not be empty")
    sample_count = len(records)
    subject_count = len({record.subject_id for record in records})
    reasons: list[str] = []
    if sample_count < requirements.minimum_samples:
        reasons.append("insufficient_validation_samples")
    if subject_count < requirements.minimum_subjects:
        reasons.append("insufficient_validation_subjects")

    candidates: list[dict[str, object]] = []
    thresholds = sorted({record.confidence for record in records if record.quality_passed})
    for threshold in thresholds:
        accepted = [
            record
            for record in records
            if record.quality_passed and record.confidence >= threshold
        ]
        successes = sum(record.dice >= requirements.dice_target for record in accepted)
        lower_bound = wilson_lower_bound(successes, len(accepted), requirements.wilson_z)
        candidates.append(
            {
                "threshold": threshold,
                "accepted": len(accepted),
                "successes": successes,
                "precision": successes / len(accepted) if accepted else 0.0,
                "precision_wilson_lower": lower_bound,
                "coverage": len(accepted) / sample_count if sample_count else 0.0,
                "passes": (
                    len(accepted) >= requirements.minimum_accepted
                    and lower_bound >= requirements.target_precision
                ),
            }
        )
    eligible = [candidate for candidate in candidates if candidate["passes"]]
    selected = max(eligible, key=lambda item: (item["coverage"], -item["threshold"])) if eligible else None
    if selected is None:
        reasons.append("no_threshold_meets_release_gate")
    passed = not reasons
    policy = {
        "policy_version": CALIBRATION_POLICY_VERSION,
        "method": CALIBRATION_METHOD,
        "status": "calibrated" if passed else "not_calibrated",
        "minimum_confidence": selected["threshold"] if passed else None,
        "calibration_version": calibration_version if passed else None,
        "validation_dataset": (
            f"{manifest['dataset_id']}@{manifest['dataset_version']}" if passed else None
        ),
        "sample_count": sample_count if passed else 0,
        "notes": (
            "Released by the held-out target-user Wilson precision gate."
            if passed
            else "Candidate rejected; production policy must remain fail-closed."
        ),
        "model_architecture": manifest["model_architecture"] if passed else None,
        "checkpoint_sha256": manifest["checkpoint_sha256"] if passed else None,
        "prediction_version": manifest["prediction_version"] if passed else None,
        "preprocessing_version": manifest["preprocessing_version"] if passed else None,
        "threshold_version": manifest["threshold_version"] if passed else None,
    }
    report = {
        "report_version": CALIBRATION_REPORT_VERSION,
        "calibration_version": calibration_version,
        "status": "passed" if passed else "failed",
        "reasons": reasons,
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "sample_count": sample_count,
            "subject_count": subject_count,
            "records_sha256": manifest.get("records_sha256"),
            "manifest_sha256": manifest.get("manifest_sha256"),
            "model_architecture": manifest["model_architecture"],
            "checkpoint_sha256": manifest["checkpoint_sha256"],
            "prediction_version": manifest["prediction_version"],
            "preprocessing_version": manifest["preprocessing_version"],
            "threshold_version": manifest["threshold_version"],
        },
        "requirements": asdict(requirements),
        "selected": selected,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "policy": policy,
    }
    return policy, report


def load_released_policy_bundle(directory: str | Path) -> ConfidencePolicy:
    """Load a policy only when its accompanying calibration report passed."""

    directory = Path(directory)
    policy_path = directory / "candidate_confidence_policy.json"
    report_path = directory / "calibration_report.json"
    policy_value = json.loads(policy_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("report_version") != CALIBRATION_REPORT_VERSION:
        raise ValueError("unsupported calibration report version")
    if report.get("status") != "passed" or report.get("reasons"):
        raise ValueError("calibration report did not pass the release gate")
    if report.get("policy") != policy_value:
        raise ValueError("candidate policy does not match its calibration report")
    if not report.get("selected") or report["selected"].get("passes") is not True:
        raise ValueError("calibration report has no passing selected threshold")
    dataset = report.get("dataset", {})
    for field in ("records_sha256", "manifest_sha256"):
        digest = dataset.get(field)
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"calibration report is missing a valid {field}")
    return ConfidencePolicy.from_dict(policy_value)
