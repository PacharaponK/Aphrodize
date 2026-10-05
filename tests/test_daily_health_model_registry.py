import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor

from backend.core.consents import MODEL_TRAINING_CONSENT_VERSION, MODEL_TRAINING_CONSENT_VERSIONS
from backend.services.daily_health_model_registry import (
    DailyHealthCandidateUnavailable,
    load_approved_candidate_bundle,
    purge_generated_candidate_artifacts,
)
from backend.services.daily_health_training import (
    ENERGY_TARGET_NAMES,
    FEATURE_AVAILABILITY_POLICY,
    FEATURE_NAMES,
    MODEL_FAMILY,
    TARGET_NAMES,
)


def make_candidate(tmp_path: Path) -> tuple[SimpleNamespace, Path]:
    version_id = "daily-health-next-day-0123456789abcdef"
    fingerprint = "a" * 64
    version_dir = tmp_path / version_id
    version_dir.mkdir()
    model = RandomForestRegressor(n_estimators=2, random_state=1).fit(
        np.asarray([[360, 1000, 1], [420, 1600, 2], [480, 1300, 3]], dtype=float),
        np.asarray([[4, 6], [2, 2], [3, 4]], dtype=float),
    )
    model_path = version_dir / "model.joblib"
    joblib.dump(model, model_path)
    metrics = {
        "validation": {"thirst": {"mae": 1.0}},
        "test": {target: {"mae": 1.0} for target in TARGET_NAMES},
        "test_mean_baseline": {target: {"mae": 2.0} for target in TARGET_NAMES},
        "temporal_test": {target: {"mae": 1.0} for target in TARGET_NAMES},
        "temporal_mean_baseline": {target: {"mae": 2.0} for target in TARGET_NAMES},
    }
    manifest = {
        "version_id": version_id,
        "model_family": MODEL_FAMILY,
        "prediction_horizon_days": 1,
        "features": FEATURE_NAMES,
        "targets": TARGET_NAMES,
        "training_records": 120,
        "participant_count": 6,
        "dataset_fingerprint": fingerprint,
        "data_policy": "active_opt_in_and_user_reported_numeric_outcomes_only",
        "synthetic_data_included": False,
        "predictions_used_as_labels": False,
        "feature_availability_policy": FEATURE_AVAILABILITY_POLICY,
        "training_consent_versions": list(MODEL_TRAINING_CONSENT_VERSIONS),
        "artifact_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "metrics": metrics,
    }
    (version_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    version = SimpleNamespace(
        version_id=version_id,
        status="candidate",
        dataset_fingerprint=fingerprint,
        model_family=MODEL_FAMILY,
        training_records=120,
        participant_count=6,
        artifact_uri=(
            "models/time-series/non-linear-model/artifacts/user-candidates/"
            f"{version_id}/model.joblib"
        ),
        metrics=metrics,
    )
    return version, model_path


def test_candidate_bundle_is_loaded_only_when_registry_and_manifest_match(tmp_path: Path) -> None:
    version, _ = make_candidate(tmp_path)

    bundle = load_approved_candidate_bundle(version, artifact_root=tmp_path)

    assert bundle["metadata"]["model_id"] == version.version_id
    assert bundle["metadata"]["prediction_horizon_days"] == 1
    assert bundle["metadata"]["holdout"]["metrics"] == version.metrics["test"]


def test_candidate_bundle_rejects_tampered_artifact_and_unapproved_paths(tmp_path: Path) -> None:
    version, model_path = make_candidate(tmp_path)
    model_path.write_bytes(model_path.read_bytes() + b"tampered")
    with pytest.raises(DailyHealthCandidateUnavailable, match="checksum"):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)

    version.artifact_uri = (
        "models/time-series/non-linear-model/artifacts/user-candidates/../../outside.joblib"
    )
    with pytest.raises(DailyHealthCandidateUnavailable, match="path"):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)


def test_candidate_bundle_refuses_stale_versions(tmp_path: Path) -> None:
    version, _ = make_candidate(tmp_path)
    version.status = "stale"

    with pytest.raises(DailyHealthCandidateUnavailable, match="approved candidate"):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)


def test_energy_candidate_requires_both_holdouts_to_beat_baseline(tmp_path: Path) -> None:
    version, model_path = make_candidate(tmp_path)
    model = RandomForestRegressor(n_estimators=2, random_state=1).fit(
        np.asarray([[360, 1000, 1], [420, 1600, 2], [480, 1300, 3]], dtype=float),
        np.asarray([[4, 6, 3], [2, 2, 8], [3, 4, 7]], dtype=float),
    )
    joblib.dump(model, model_path)
    manifest_path = model_path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["targets"] = ENERGY_TARGET_NAMES
    manifest["training_consent_versions"] = [MODEL_TRAINING_CONSENT_VERSION]
    manifest["artifact_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    for split in ("test", "temporal_test"):
        version.metrics[split]["reported_energy_level_0_10"] = {"mae": 1.0}
    for split in ("test_mean_baseline", "temporal_mean_baseline"):
        version.metrics[split]["reported_energy_level_0_10"] = {"mae": 2.0}
    manifest["metrics"] = version.metrics
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    bundle = load_approved_candidate_bundle(version, artifact_root=tmp_path)
    assert bundle["metadata"]["targets"] == ENERGY_TARGET_NAMES

    version.metrics["temporal_test"]["reported_energy_level_0_10"]["mae"] = 2.0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DailyHealthCandidateUnavailable, match="outperform"):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)

    version.metrics.pop("temporal_test")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DailyHealthCandidateUnavailable, match="baseline metrics"):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)


def test_candidate_purge_removes_only_manifested_generated_outputs(tmp_path: Path) -> None:
    version, model_path = make_candidate(tmp_path)
    manifest_path = model_path.parent / "manifest.json"

    removed = purge_generated_candidate_artifacts([version.version_id], artifact_root=tmp_path)

    assert removed == 2
    assert not model_path.exists()
    assert not manifest_path.exists()
    assert not model_path.parent.exists()


@pytest.mark.parametrize("target", TARGET_NAMES)
@pytest.mark.parametrize("split", ["test", "temporal_test"])
@pytest.mark.parametrize("mae", [2.0, 3.0, -1.0, float("nan"), float("inf"), True])
def test_all_targets_must_improve_both_holdouts(tmp_path, target, split, mae):
    version, model_path = make_candidate(tmp_path)
    version.metrics[split][target]["mae"] = mae
    (model_path.parent / "manifest.json").write_text(
        json.dumps({**json.loads((model_path.parent / "manifest.json").read_text()),
                    "metrics": version.metrics}), encoding="utf-8")
    with pytest.raises(DailyHealthCandidateUnavailable):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)


def test_old_candidate_without_as_of_policy_cannot_be_promoted(tmp_path):
    version, model_path = make_candidate(tmp_path)
    path = model_path.parent / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.pop("feature_availability_policy")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(DailyHealthCandidateUnavailable):
        load_approved_candidate_bundle(version, artifact_root=tmp_path)


def test_candidate_purge_rejects_unknown_files_without_deleting_anything(tmp_path: Path) -> None:
    version, model_path = make_candidate(tmp_path)
    private_file = model_path.parent / "do-not-delete.txt"
    private_file.write_text("unknown content", encoding="utf-8")

    with pytest.raises(DailyHealthCandidateUnavailable, match="unrecognized files"):
        purge_generated_candidate_artifacts([version.version_id], artifact_root=tmp_path)

    assert model_path.exists()
    assert private_file.exists()
