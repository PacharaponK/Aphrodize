import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai.ffhq_wrinkle.calibration import (
    CALIBRATION_POLICY_VERSION,
    CalibrationRequirements,
    ValidationRecord,
    calibrate_confidence,
    load_and_validate_dataset,
    load_released_policy_bundle,
    wilson_lower_bound,
)
from ai.ffhq_wrinkle.confidence import ConfidencePolicy


def records():
    result = []
    for index in range(120):
        good = index >= 20
        result.append(
            ValidationRecord(
                sample_id=f"sample-{index:03d}",
                subject_id=f"subject-{index:03d}",
                confidence=0.8 if good else 0.2,
                dice=0.8 if good else 0.2,
                quality_passed=True,
            )
        )
    return result


def manifest(sample_count=120, subject_count=120):
    return {
        "manifest_version": "aphrodize-target-user-validation-v1",
        "dataset_id": "target-user-heldout",
        "dataset_version": "2026-09-22-v1",
        "purpose": "confidence_calibration",
        "source_kind": "target_user",
        "consent_scope": ["validation"],
        "identity_split_method": "subject-disjoint assignment",
        "independent_from_training": True,
        "independent_from_official_test": True,
        "official_test_overlap_count": 0,
        "sample_count": sample_count,
        "subject_count": subject_count,
        "capture_protocol": "capture-v1",
        "annotation_guideline": "wrinkle-mask-v1",
        "model_architecture": "UNet",
        "checkpoint_sha256": "a" * 64,
        "prediction_version": "prediction-v1",
        "preprocessing_version": "preprocess-v1",
        "threshold_version": "threshold-v1",
        "confidence_method": "mean-binary-decision-margin",
        "records_sha256": "filled-by-fixture",
    }


class CalibrationTests(unittest.TestCase):
    def test_wilson_lower_bound(self):
        self.assertGreater(wilson_lower_bound(100, 100), 0.96)
        self.assertLess(wilson_lower_bound(50, 100), 0.5)
        self.assertEqual(wilson_lower_bound(0, 0), 0.0)

    def test_selects_widest_coverage_passing_threshold(self):
        policy, report = calibrate_confidence(records(), manifest(), "calibration-v1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(policy["policy_version"], CALIBRATION_POLICY_VERSION)
        self.assertEqual(policy["status"], "calibrated")
        self.assertEqual(policy["minimum_confidence"], 0.8)
        self.assertEqual(report["selected"]["accepted"], 100)
        ConfidencePolicy.from_dict(policy)

    def test_no_passing_threshold_remains_fail_closed(self):
        poor = [ValidationRecord(f"s-{i}", f"p-{i}", 0.9, 0.1, True) for i in range(120)]
        policy, report = calibrate_confidence(poor, manifest(), "calibration-v1")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(policy["status"], "not_calibrated")
        self.assertIsNone(policy["minimum_confidence"])
        self.assertIn("no_threshold_meets_release_gate", report["reasons"])

    def test_insufficient_dataset_cannot_release_policy(self):
        small = records()[:20]
        policy, report = calibrate_confidence(small, manifest(20, 20), "calibration-v1")
        self.assertEqual(policy["status"], "not_calibrated")
        self.assertIn("insufficient_validation_samples", report["reasons"])
        self.assertIn("insufficient_validation_subjects", report["reasons"])

    def test_requirements_are_validated(self):
        with self.assertRaises(ValueError):
            CalibrationRequirements(target_precision=1.1).validate()


class ValidationDatasetTests(unittest.TestCase):
    def write_fixture(self, directory, mutate_manifest=None):
        csv_path = Path(directory) / "validation.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["sample_id", "subject_id", "confidence", "dice", "quality_passed"],
            )
            writer.writeheader()
            for record in records():
                writer.writerow(
                    {
                        "sample_id": record.sample_id,
                        "subject_id": record.subject_id,
                        "confidence": record.confidence,
                        "dice": record.dice,
                        "quality_passed": str(record.quality_passed).lower(),
                    }
                )
        value = manifest()
        value["records_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        if mutate_manifest:
            mutate_manifest(value)
        manifest_path = Path(directory) / "manifest.json"
        manifest_path.write_text(json.dumps(value), encoding="utf-8")
        return csv_path, manifest_path

    def test_manifest_and_records_are_bound_by_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path, manifest_path = self.write_fixture(directory)
            loaded, value = load_and_validate_dataset(csv_path, manifest_path)
            self.assertEqual(len(loaded), 120)
            self.assertEqual(value["dataset_id"], "target-user-heldout")
            with csv_path.open("a", encoding="utf-8") as handle:
                handle.write("tampered,row,0.5,0.5,true\n")
            with self.assertRaises(ValueError):
                load_and_validate_dataset(csv_path, manifest_path)

    def test_training_or_official_test_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path, manifest_path = self.write_fixture(
                directory,
                lambda value: value.update(
                    independent_from_training=False,
                    official_test_overlap_count=1,
                ),
            )
            with self.assertRaisesRegex(ValueError, "independent from training"):
                load_and_validate_dataset(csv_path, manifest_path)

    def test_release_bundle_requires_matching_passed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path, manifest_path = self.write_fixture(directory)
            loaded, value = load_and_validate_dataset(csv_path, manifest_path)
            policy, report = calibrate_confidence(loaded, value, "calibration-v1")
            bundle = Path(directory) / "bundle"
            bundle.mkdir()
            policy_path = bundle / "candidate_confidence_policy.json"
            report_path = bundle / "calibration_report.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            report_path.write_text(json.dumps(report), encoding="utf-8")
            released = load_released_policy_bundle(bundle)
            self.assertEqual(released.minimum_confidence, 0.8)
            policy["minimum_confidence"] = 0.1
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                load_released_policy_bundle(bundle)

    def test_calibration_cli_writes_releasable_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path, manifest_path = self.write_fixture(directory)
            output = Path(directory) / "output"
            repository = Path(__file__).resolve().parents[2]
            completed = subprocess.run(
                [
                    sys.executable,
                    str(repository / "ai" / "scripts" / "calibrate_ffhq_wrinkle_confidence.py"),
                    "--records",
                    str(csv_path),
                    "--manifest",
                    str(manifest_path),
                    "--calibration-version",
                    "calibration-cli-test-v1",
                    "--output",
                    str(output),
                ],
                cwd=repository,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(load_released_policy_bundle(output).minimum_confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
