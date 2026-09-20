"""Deterministic, mask-based wrinkle scoring prototype.

This is an evaluation utility, not a wrinkle-segmentation model.  It consumes
an image plus an existing wrinkle mask, which makes it useful for checking
FFHQ-Wrinkle label pairs and defining the API contract before model inference
is integrated.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SCORE_VERSION = "mask-area-v1"


@dataclass(frozen=True)
class PreprocessConfig:
    image_size: int = 512
    mask_threshold: int = 127
    score_scale: float = 2000.0


def load_image(path: Path) -> Image.Image:
    """Load a local user/dataset image without retaining it outside process."""
    with Image.open(path) as opened:
        return opened.convert("RGB").copy()


def load_mask(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return opened.convert("L").copy()


def preprocess(image: Image.Image, mask: Image.Image, config: PreprocessConfig) -> tuple[np.ndarray, np.ndarray]:
    """Resize consistently; return image [0,1] and boolean binary mask."""
    size = (config.image_size, config.image_size)
    image_arr = np.asarray(image.resize(size, Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    mask_arr = np.asarray(mask.resize(size, Image.Resampling.NEAREST), dtype=np.uint8)
    return image_arr, mask_arr > config.mask_threshold


def quality_flags(image: Image.Image) -> list[str]:
    """Small, explainable pre-inference checks; no face/identity analysis."""
    flags: list[str] = []
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    if min(image.size) < 256:
        flags.append("low_resolution")
    mean = float(gray.mean())
    if mean < 45:
        flags.append("underexposed")
    elif mean > 210:
        flags.append("overexposed")
    sharpness = float(np.asarray(image.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32).var())
    if sharpness < 25:
        flags.append("possibly_blurry")
    return flags


def score_mask(mask: np.ndarray, config: PreprocessConfig) -> dict[str, Any]:
    """Score is clipped area density, deliberately simple and versioned.

    score = min(100, 100 * wrinkle_area_ratio * score_scale / 100).
    With the default scale this is min(100, ratio * 2000). It is not a
    clinical severity scale and must not be compared to another score version.
    """
    ratio = float(mask.mean())
    score = min(100.0, ratio * config.score_scale)
    severity = "none" if ratio == 0 else "mild" if score < 33 else "moderate" if score < 67 else "high"
    return {
        "wrinkle_pixels": int(mask.sum()),
        "evaluated_pixels": int(mask.size),
        "wrinkle_area_ratio": round(ratio, 8),
        "wrinkle_score": round(score, 2),
        "severity": severity,
        "score_version": SCORE_VERSION,
    }


def analyze(image_path: Path, mask_path: Path, config: PreprocessConfig) -> dict[str, Any]:
    image, mask = load_image(image_path), load_mask(mask_path)
    image_array, binary_mask = preprocess(image, mask, config)
    result = score_mask(binary_mask, config)
    result.update({
        "image": {"path": str(image_path), "original_size": list(image.size), "preprocessed_shape": list(image_array.shape)},
        "mask": {"path": str(mask_path), "original_size": list(mask.size), "threshold": config.mask_threshold},
        "quality_flags": quality_flags(image),
    })
    return result


def find_image(root: Path, stem: str) -> Path | None:
    matches = [p for p in root.rglob("*") if p.is_file() and p.stem == stem and p.suffix.lower() in SUPPORTED_SUFFIXES]
    return matches[0] if len(matches) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Score paired wrinkle masks deterministically.")
    parser.add_argument("--image", type=Path, help="Single RGB image path")
    parser.add_argument("--mask", type=Path, help="Single grayscale wrinkle-mask path")
    parser.add_argument("--data-root", type=Path, help="FFHQ-Wrinkle root; expects images1024x1024 and manual_wrinkle_masks")
    parser.add_argument("--limit", type=int, default=10, help="Maximum pairs in --data-root mode")
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--output", type=Path, default=Path("storage/artifacts/non_time_serie/wrinkle_prototype/results.json"))
    args = parser.parse_args()
    config = PreprocessConfig(image_size=args.image_size)
    if bool(args.image) != bool(args.mask) and not args.data_root:
        parser.error("--image and --mask must be supplied together")
    if args.image and args.mask:
        results = [analyze(args.image, args.mask, config)]
    elif args.data_root:
        masks = args.data_root / "manual_wrinkle_masks"
        images = args.data_root / "images1024x1024"
        if not masks.is_dir() or not images.is_dir():
            parser.error("dataset needs manual_wrinkle_masks/ and images1024x1024/")
        pairs = [(find_image(images, m.stem), m) for m in sorted(masks.glob("*.png"))]
        results = [analyze(image, mask, config) for image, mask in pairs if image is not None][:args.limit]
    else:
        parser.error("provide --image/--mask or --data-root")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"prototype": "ffhq-wrinkle-mask-score", "score_version": SCORE_VERSION, "count": len(results), "results": results}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "count": len(results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
