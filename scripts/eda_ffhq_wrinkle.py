"""Create a reproducible EDA report for the FFHQ-Wrinkle manual-label set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


def image_path_for_mask(images_root: Path, mask_path: Path) -> Path:
    image_id = int(mask_path.stem)
    return images_root / f"{(image_id // 1000) * 1000:05d}" / mask_path.name


def inspect_pair(mask_path: Path, image_path: Path) -> dict[str, object]:
    with Image.open(mask_path) as mask_file:
        mask = np.asarray(mask_file.convert("L"))
    with Image.open(image_path) as image_file:
        image_size = image_file.size
    wrinkle_pixels = int(np.count_nonzero(mask))
    total_pixels = int(mask.size)
    return {
        "image_id": mask_path.stem,
        "mask_path": str(mask_path),
        "image_path": str(image_path),
        "mask_width": int(mask.shape[1]),
        "mask_height": int(mask.shape[0]),
        "image_width": image_size[0],
        "image_height": image_size[1],
        "unique_mask_values": "|".join(map(str, np.unique(mask).tolist())),
        "wrinkle_pixels": wrinkle_pixels,
        "total_pixels": total_pixels,
        "wrinkle_area_ratio": wrinkle_pixels / total_pixels,
        "size_matches": image_size == (mask.shape[1], mask.shape[0]),
    }


def write_sample_grid(metrics: pd.DataFrame, output_path: Path, sample_count: int, seed: int) -> None:
    sample = metrics.sample(n=min(sample_count, len(metrics)), random_state=seed)
    fig, axes = plt.subplots(len(sample), 3, figsize=(12, 4 * len(sample)))
    axes = np.atleast_2d(axes)
    for row_axes, (_, row) in zip(axes, sample.iterrows(), strict=True):
        with Image.open(row.image_path) as image_file:
            image = np.asarray(image_file.convert("RGB"))
        with Image.open(row.mask_path) as mask_file:
            mask = np.asarray(mask_file.convert("L"))
        overlay = image.copy()
        overlay[mask > 0] = (255, 60, 60)
        for axis, display, title in zip(
            row_axes, (image, mask, overlay), ("Face image", "Wrinkle mask", "Mask overlay"), strict=True
        ):
            axis.imshow(display, cmap="gray" if display.ndim == 2 else None)
            axis.set_title(title)
            axis.axis("off")
        row_axes[0].set_ylabel(
            f"ID {row.image_id}\narea={row.wrinkle_area_ratio:.3%}", rotation=0, labelpad=62, va="center"
        )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="EDA for FFHQ-Wrinkle manual masks")
    parser.add_argument("--data-root", type=Path, required=True, help="Contains images1024x1024 and manual_wrinkle_masks")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/ffhq_wrinkle_eda"))
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    images_root = args.data_root / "images1024x1024"
    masks_root = args.data_root / "manual_wrinkle_masks"
    if not images_root.is_dir() or not masks_root.is_dir():
        parser.error("--data-root must contain images1024x1024/ and manual_wrinkle_masks/")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    present, missing = [], []
    mask_paths = sorted(masks_root.glob("*.png"))
    for mask_path in mask_paths:
        image_path = image_path_for_mask(images_root, mask_path)
        if image_path.is_file():
            present.append(inspect_pair(mask_path, image_path))
        else:
            missing.append({"image_id": mask_path.stem, "expected_image_path": str(image_path)})

    metrics = pd.DataFrame(present)
    metrics.to_csv(args.output_dir / "manual_mask_metrics.csv", index=False)
    pd.DataFrame(missing).to_csv(args.output_dir / "missing_images.csv", index=False)
    if metrics.empty:
        parser.error("No matching image/mask pairs found; see missing_images.csv")

    summary = {
        "manual_masks_found": len(mask_paths),
        "matched_image_mask_pairs": len(metrics),
        "missing_source_images": len(missing),
        "all_dimensions_match": bool(metrics["size_matches"].all()),
        "mask_sizes": {f"{width}x{height}": int(count) for (width, height), count in metrics[["mask_width", "mask_height"]].value_counts().items()},
        "wrinkle_area_ratio": {key: float(getattr(metrics.wrinkle_area_ratio, key)()) for key in ("min", "median", "mean", "max")},
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plt.figure(figsize=(8, 5))
    plt.hist(metrics.wrinkle_area_ratio, bins=30, color="#8b5cf6", edgecolor="white")
    plt.xlabel("Wrinkle area ratio")
    plt.ylabel("Images")
    plt.title("FFHQ-Wrinkle manual-mask distribution")
    plt.tight_layout()
    plt.savefig(args.output_dir / "wrinkle_area_histogram.png", dpi=150)
    plt.close()
    write_sample_grid(metrics, args.output_dir / "sample_pairs.png", args.samples, args.seed)
    print(f"EDA complete: {args.output_dir.resolve()}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
