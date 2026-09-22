"""Evaluate FFHQ-Wrinkle checkpoints on the recorded official test IDs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.ffhq_wrinkle.evaluation import run_evaluation
from ai.ffhq_wrinkle.prediction import ThresholdConfig


def build_parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=repository_root / "ai" / "ffhq-wrinkle",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--network",
        choices=("both", "UNet", "SwinUNETR"),
        default="both",
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--limit", type=int, help="smoke-test only; full reports must omit this")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite:
        print(json.dumps({"status": "refused", "error": "output directory is not empty; use --overwrite"}))
        return 3
    architectures = ["UNet", "SwinUNETR"] if args.network == "both" else [args.network]
    result = run_evaluation(
        args.data_root,
        args.output,
        architectures,
        args.device,
        ThresholdConfig(probability=args.threshold),
        args.limit,
    )
    display = {
        "evaluation_version": result["evaluation_version"],
        "dataset": result["dataset"],
        "models": [
            {
                "architecture": model["architecture"],
                "overall": model["overall"],
                "inference_latency_seconds": model["inference_latency_seconds"],
            }
            for model in result["models"]
        ],
    }
    print(json.dumps(display, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
