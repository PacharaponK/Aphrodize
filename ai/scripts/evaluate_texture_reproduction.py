"""Compare texture-map implementation variants with official weak masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from ai.ffhq_wrinkle.face_parsing import face_mask_from_labels, load_label_map
from ai.ffhq_wrinkle.paths import DATA_ROOT
from ai.ffhq_wrinkle.texture_map import TextureMapConfig, generate_texture_map


def image_path_for_id(root: Path, image_id: str) -> Path:
    group = int(image_id) - int(image_id) % 1_000
    return root / f"{group:05d}" / f"{image_id}.png"


def evaluate_config(
    image_ids: list[str],
    images_root: Path,
    labels_root: Path,
    weak_root: Path,
    config: TextureMapConfig,
) -> dict[str, object]:
    absolute_error = 0
    squared_error = 0
    exact_pixels = 0
    total_pixels = 0
    per_image: list[dict[str, object]] = []
    for image_id in image_ids:
        image = np.asarray(Image.open(image_path_for_id(images_root, image_id)).convert("RGB"))
        labels = load_label_map(labels_root / f"{image_id}.npy")
        face_mask = face_mask_from_labels(labels, image.shape[:2])
        predicted = generate_texture_map(image, face_mask, config)
        official = np.asarray(Image.open(image_path_for_id(weak_root, image_id)).convert("L"))
        difference = predicted.astype(np.int16) - official.astype(np.int16)
        abs_difference = np.abs(difference)
        image_mae = float(abs_difference.mean())
        per_image.append(
            {
                "id": image_id,
                "mae": image_mae,
                "max_absolute_error": int(abs_difference.max()),
                "exact_pixel_ratio": float(np.mean(difference == 0)),
            }
        )
        absolute_error += int(abs_difference.sum(dtype=np.int64))
        squared_error += int(np.square(difference.astype(np.int32)).sum(dtype=np.int64))
        exact_pixels += int(np.count_nonzero(difference == 0))
        total_pixels += difference.size
    return {
        "config": config.__dict__,
        "image_count": len(image_ids),
        "pixel_count": total_pixels,
        "mae": absolute_error / total_pixels,
        "rmse": (squared_error / total_pixels) ** 0.5,
        "exact_pixel_ratio": exact_pixels / total_pixels,
        "per_image": per_image,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", type=Path, default=DATA_ROOT / "test_file_lists.txt")
    parser.add_argument("--images", type=Path, default=DATA_ROOT / "images1024x1024")
    parser.add_argument("--labels", type=Path, default=DATA_ROOT / "face-parsed-labels")
    parser.add_argument("--weak", type=Path, default=DATA_ROOT / "weak_wrinkle_masks")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--intensity",
        choices=(
            "opencv_gray",
            "opencv_bgr_on_rgb",
            "pillow_gray",
            "bt601_float",
            "bt709_float",
            "rgb_channels",
            "rgb_mean",
            "red",
            "green",
            "blue",
        ),
        default=TextureMapConfig().intensity_method,
    )
    parser.add_argument(
        "--blur-dtype", choices=("uint8", "float32"), default=TextureMapConfig().blur_dtype
    )
    parser.add_argument(
        "--border", choices=("reflect101", "reflect", "replicate", "constant"), default="reflect101"
    )
    parser.add_argument(
        "--rounding", choices=("truncate", "round"), default=TextureMapConfig().rounding
    )
    parser.add_argument(
        "--response-mode",
        choices=("clip", "absolute", "wrap", "dark_only_floor"),
        default=TextureMapConfig().response_mode,
    )
    parser.add_argument(
        "--channel-reduction",
        choices=(
            "before_quantize",
            "after_quantize",
            "max_after_quantize",
            "mean_after_quantize",
        ),
        default="after_quantize",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--summary-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    image_ids = [
        line.strip() for line in args.ids.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if args.limit is not None:
        image_ids = image_ids[: args.limit]
    config = TextureMapConfig(
        intensity_method=args.intensity,
        blur_dtype=args.blur_dtype,
        border=args.border,
        rounding=args.rounding,
        response_mode=args.response_mode,
        channel_reduction=args.channel_reduction,
    )
    result = evaluate_config(image_ids, args.images, args.labels, args.weak, config)
    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    displayed = (
        {key: value for key, value in result.items() if key != "per_image"}
        if args.summary_only
        else result
    )
    print(json.dumps(displayed, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
