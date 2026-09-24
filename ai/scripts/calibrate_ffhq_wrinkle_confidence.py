"""Calibrate a candidate confidence policy from held-out target-user validation data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.ffhq_wrinkle.calibration import (
    CalibrationRequirements,
    calibrate_confidence,
    load_and_validate_dataset,
)


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--calibration-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-samples", type=int, default=100)
    parser.add_argument("--minimum-subjects", type=int, default=50)
    parser.add_argument("--minimum-accepted", type=int, default=30)
    parser.add_argument("--target-precision", type=float, default=0.90)
    parser.add_argument("--dice-target", type=float, default=0.60)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory must be absent or empty")
    records, manifest = load_and_validate_dataset(args.records, args.manifest)
    requirements = CalibrationRequirements(
        minimum_samples=args.minimum_samples,
        minimum_subjects=args.minimum_subjects,
        minimum_accepted=args.minimum_accepted,
        target_precision=args.target_precision,
        dice_target=args.dice_target,
    )
    policy, report = calibrate_confidence(records, manifest, args.calibration_version, requirements)
    args.output.mkdir(parents=True, exist_ok=True)
    _write_json(args.output / "candidate_confidence_policy.json", policy)
    _write_json(args.output / "calibration_report.json", report)
    print(json.dumps({"status": report["status"], "reasons": report["reasons"]}))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
