"""Build a Phase 6 public-response fixture from an existing Phase 4 prediction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ffhq_wrinkle.prediction import PredictionResult
from ffhq_wrinkle.service import WrinkleAnalysisService


def build_public_response(prediction_dir: Path) -> dict[str, object]:
    metadata = json.loads((prediction_dir / "result.json").read_text(encoding="utf-8"))
    probability = np.load(prediction_dir / "wrinkle_probability.npy", allow_pickle=False)
    with Image.open(prediction_dir / "wrinkle_mask.png") as opened:
        mask = np.asarray(opened.convert("L")) > 0
    with Image.open(prediction_dir / "face_mask.png") as opened:
        face_mask = np.asarray(opened.convert("L")) > 0
    result = PredictionResult(
        logits=np.empty((0,), dtype=np.float32),
        probability=probability,
        mask=mask,
        overlay=np.empty((0,), dtype=np.uint8),
        metadata=metadata,
    )
    return WrinkleAnalysisService().build_response(result, face_mask).model_dump()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    response = build_public_response(args.prediction)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": response["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
