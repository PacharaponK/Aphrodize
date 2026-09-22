"""Versioned, non-clinical scores derived from wrinkle segmentation masks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ROI_VERSION = "ffhq-aligned-roi-v1"
SCORE_VERSION = "aphrodize-wrinkle-area-v1"
SCORE_DISCLAIMER = (
    "A model-derived image measurement for research use; it is not a diagnosis, "
    "a clinical severity rating, or evidence that any treatment will work."
)


@dataclass(frozen=True)
class ScoreConfig:
    """Configuration for mapping visible segmented area to an application score."""

    scale: float = 2000.0
    low_boundary: float = 33.0
    high_boundary: float = 67.0
    score_version: str = SCORE_VERSION
    roi_version: str = ROI_VERSION

    def validate(self) -> None:
        if self.scale <= 0:
            raise ValueError("score scale must be positive")
        if not 0 <= self.low_boundary < self.high_boundary <= 100:
            raise ValueError("score boundaries must satisfy 0 <= low < high <= 100")
        if not self.score_version or not self.roi_version:
            raise ValueError("score and ROI versions must not be empty")


def _box(shape: tuple[int, int], x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
    height, width = shape
    mask = np.zeros(shape, dtype=bool)
    xa, xb = int(round(x0 * width)), int(round(x1 * width))
    ya, yb = int(round(y0 * height)), int(round(y1 * height))
    mask[max(0, ya) : min(height, yb), max(0, xa) : min(width, xb)] = True
    return mask


def _ellipse(
    shape: tuple[int, int], center_x: float, center_y: float, radius_x: float, radius_y: float
) -> np.ndarray:
    height, width = shape
    yy, xx = np.ogrid[:height, :width]
    cx, cy = center_x * width, center_y * height
    rx, ry = max(radius_x * width, 1.0), max(radius_y * height, 1.0)
    return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0


def build_regional_rois(face_mask: np.ndarray) -> dict[str, np.ndarray]:
    """Build deterministic ROIs in normalized FFHQ-aligned image coordinates.

    Left/right names are image-relative to avoid claiming anatomical orientation.
    Every ROI is intersected with the face-parsing mask.
    """

    if face_mask.ndim != 2:
        raise ValueError("face_mask must be a two-dimensional array")
    face = face_mask.astype(bool)
    shape = face.shape
    rois = {
        "forehead": _box(shape, 0.25, 0.12, 0.75, 0.38),
        "glabella": _box(shape, 0.42, 0.32, 0.58, 0.50),
        "image_left_periocular": _ellipse(shape, 0.34, 0.46, 0.16, 0.12),
        "image_right_periocular": _ellipse(shape, 0.66, 0.46, 0.16, 0.12),
        "image_left_cheek": _ellipse(shape, 0.34, 0.66, 0.17, 0.17),
        "image_right_cheek": _ellipse(shape, 0.66, 0.66, 0.17, 0.17),
        "nasolabial": (
            _ellipse(shape, 0.43, 0.66, 0.075, 0.18)
            | _ellipse(shape, 0.57, 0.66, 0.075, 0.18)
        ),
        "perioral": _ellipse(shape, 0.50, 0.77, 0.20, 0.12),
    }
    return {name: roi & face for name, roi in rois.items()}


def _severity_label(score: float, config: ScoreConfig) -> str:
    if score == 0:
        return "no_segmented_area"
    if score < config.low_boundary:
        return "low_visible_area"
    if score < config.high_boundary:
        return "medium_visible_area"
    return "high_visible_area"


def _score(mask: np.ndarray, evaluation_mask: np.ndarray, config: ScoreConfig) -> dict[str, object]:
    evaluated_pixels = int(np.count_nonzero(evaluation_mask))
    wrinkle_pixels = int(np.count_nonzero(mask & evaluation_mask))
    ratio = wrinkle_pixels / evaluated_pixels if evaluated_pixels else 0.0
    value = min(100.0, ratio * config.scale)
    return {
        "score": round(value, 4),
        "severity_label": _severity_label(value, config),
        "wrinkle_area_ratio": ratio,
        "wrinkle_pixels": wrinkle_pixels,
        "evaluated_pixels": evaluated_pixels,
        "score_version": config.score_version,
        "roi_version": config.roi_version,
    }


def derive_scores(
    wrinkle_mask: np.ndarray,
    face_mask: np.ndarray,
    *,
    gate_passed: bool,
    config: ScoreConfig = ScoreConfig(),
) -> dict[str, object]:
    """Derive versioned scores only after quality and confidence gates pass."""

    config.validate()
    if not gate_passed:
        raise PermissionError("derived scores require passed quality and confidence gates")
    if wrinkle_mask.shape != face_mask.shape or wrinkle_mask.ndim != 2:
        raise ValueError("wrinkle_mask and face_mask must be matching 2-D arrays")
    wrinkle = wrinkle_mask.astype(bool)
    face = face_mask.astype(bool)
    return {
        "score_version": config.score_version,
        "roi_version": config.roi_version,
        "formula": f"min(100, wrinkle_area_ratio * {config.scale:g})",
        "overall": _score(wrinkle, face, config),
        "regions": {
            name: _score(wrinkle, roi, config)
            for name, roi in build_regional_rois(face).items()
        },
        "disclaimer": SCORE_DISCLAIMER,
    }
