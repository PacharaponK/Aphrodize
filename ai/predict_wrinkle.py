"""CLI for one-image FFHQ-Wrinkle prediction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.ffhq_wrinkle.prediction import ThresholdConfig, predict_image
from ai.ffhq_wrinkle.quality import QualityGateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--network", choices=("UNet", "SwinUNETR"), default="UNet")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly replace managed artifacts in a non-empty output directory",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = predict_image(
            image_path=args.image,
            output_dir=args.output,
            architecture=args.network,
            checkpoint_path=args.checkpoint,
            requested_device=args.device,
            threshold=ThresholdConfig(probability=args.threshold),
            overwrite=args.overwrite,
        )
    except QualityGateError as error:
        print(json.dumps({"status": "rejected", "quality_flags": error.assessment.issues}))
        return 2
    except FileExistsError as error:
        print(json.dumps({"status": "refused", "error": str(error)}))
        return 3
    print(json.dumps(result.metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
