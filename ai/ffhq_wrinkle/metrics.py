"""Binary segmentation metrics used by FFHQ-Wrinkle evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class BinaryConfusion:
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0

    def __add__(self, other: "BinaryConfusion") -> "BinaryConfusion":
        return BinaryConfusion(
            self.true_positive + other.true_positive,
            self.false_positive + other.false_positive,
            self.false_negative + other.false_negative,
            self.true_negative + other.true_negative,
        )

    @property
    def pixels(self) -> int:
        return self.true_positive + self.false_positive + self.false_negative + self.true_negative


def binary_confusion(prediction: np.ndarray, target: np.ndarray) -> BinaryConfusion:
    if prediction.shape != target.shape:
        raise ValueError("prediction and target shapes must match")
    predicted = prediction.astype(bool)
    actual = target.astype(bool)
    return BinaryConfusion(
        true_positive=int(np.count_nonzero(predicted & actual)),
        false_positive=int(np.count_nonzero(predicted & ~actual)),
        false_negative=int(np.count_nonzero(~predicted & actual)),
        true_negative=int(np.count_nonzero(~predicted & ~actual)),
    )


def metrics_from_confusion(confusion: BinaryConfusion) -> dict[str, float | int]:
    tp = confusion.true_positive
    fp = confusion.false_positive
    fn = confusion.false_negative
    predicted_positive = tp + fp
    actual_positive = tp + fn
    dice_denominator = 2 * tp + fp + fn
    iou_denominator = tp + fp + fn
    dice = 1.0 if dice_denominator == 0 else 2.0 * tp / dice_denominator
    iou = 1.0 if iou_denominator == 0 else tp / iou_denominator
    precision = (1.0 if actual_positive == 0 else 0.0) if predicted_positive == 0 else tp / predicted_positive
    recall = 1.0 if actual_positive == 0 else tp / actual_positive
    pixel_count = confusion.pixels
    values: dict[str, float | int] = {
        **asdict(confusion),
        "pixel_count": pixel_count,
        "dice": dice,
        "iou": iou,
        "precision": precision,
        "recall": recall,
        "false_positive_area": fp / pixel_count if pixel_count else 0.0,
        "predicted_positive_area": predicted_positive / pixel_count if pixel_count else 0.0,
        "target_positive_area": actual_positive / pixel_count if pixel_count else 0.0,
    }
    return values


def mean_metric(rows: list[dict[str, object]], key: str) -> float:
    if not rows:
        return 0.0
    return float(np.mean([float(row[key]) for row in rows]))


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    total = BinaryConfusion()
    for row in rows:
        total += BinaryConfusion(
            int(row["true_positive"]),
            int(row["false_positive"]),
            int(row["false_negative"]),
            int(row["true_negative"]),
        )
    return {
        "image_count": len(rows),
        "micro": metrics_from_confusion(total),
        "macro": {
            key: mean_metric(rows, key)
            for key in (
                "dice",
                "iou",
                "precision",
                "recall",
                "false_positive_area",
            )
        },
    }
