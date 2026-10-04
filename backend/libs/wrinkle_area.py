"""Provisional visible-area bands for research audits, not clinical severity."""

from math import isfinite

AREA_BAND_VERSION = "visible-area-provisional-v1"
AREA_BANDS = ("none", "low", "medium", "high")


def assess_visible_area(
    wrinkle_pixels: int,
    evaluated_pixels: int,
    *,
    low_ratio: float = 0.0165,
    high_ratio: float = 0.0335,
) -> dict:
    """Preserve uncapped area; defaults reproduce existing 33/67 score boundaries."""
    if not all(type(value) is int for value in (wrinkle_pixels, evaluated_pixels)):
        raise ValueError("pixel counts must be integers")
    if not 0 <= wrinkle_pixels <= evaluated_pixels:
        raise ValueError("require 0 <= wrinkle_pixels <= evaluated_pixels")
    if (
        not all(
            type(value) in (int, float) and isfinite(value) for value in (low_ratio, high_ratio)
        )
        or not 0 < low_ratio < high_ratio <= 1
    ):
        raise ValueError("require finite 0 < low_ratio < high_ratio <= 1")
    ratio = wrinkle_pixels / evaluated_pixels if evaluated_pixels else None
    band = (
        "unavailable"
        if ratio is None
        else "none"
        if ratio == 0
        else "low"
        if ratio < low_ratio
        else "medium"
        if ratio < high_ratio
        else "high"
    )
    return {
        "area_band_version": AREA_BAND_VERSION,
        "validation_status": "not_validated",
        "recommendation_ready": False,
        "wrinkle_area_ratio": ratio,
        "visible_area_band": band,
        "thresholds": {"low_ratio": low_ratio, "high_ratio": high_ratio},
    }
