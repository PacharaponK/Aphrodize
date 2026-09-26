"""Reject source photos that cannot produce a trustworthy model input.

The first gate inspects the original photo and YuNet detection. A second gate
checks how much of the aligned image BiSeNet marked as skin/nose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .alignment import FaceDetection


@dataclass(frozen=True)
class QualityConfig:
    minimum_width: int = 256
    minimum_height: int = 256
    minimum_face_pixels: float = 120.0
    minimum_face_ratio: float = 0.18
    minimum_landmark_confidence: float = 0.60
    minimum_luma: float = 35.0
    maximum_luma: float = 220.0
    maximum_clipped_ratio: float = 0.35
    minimum_laplacian_variance: float = 40.0
    maximum_roll_degrees: float = 15.0
    maximum_yaw_proxy: float = 0.35
    minimum_pitch_proxy: float = 0.25
    maximum_pitch_proxy: float = 0.80
    minimum_face_mask_ratio: float = 0.08
    maximum_face_mask_ratio: float = 0.75


@dataclass(frozen=True)
class QualityAssessment:
    passed: bool
    issues: tuple[str, ...]
    metrics: dict[str, float | int]


class QualityGateError(RuntimeError):
    def __init__(self, assessment: QualityAssessment):
        self.assessment = assessment
        super().__init__("quality gate rejected image: " + ", ".join(assessment.issues))


def _face_crop(image: np.ndarray, detection: FaceDetection) -> np.ndarray:
    x, y, width, height = detection.bbox
    image_height, image_width = image.shape[:2]
    x0 = max(0, int(np.floor(x)))
    y0 = max(0, int(np.floor(y)))
    x1 = min(image_width, int(np.ceil(x + width)))
    y1 = min(image_height, int(np.ceil(y + height)))
    if x1 <= x0 or y1 <= y0:
        return image[0:0, 0:0]
    return image[y0:y1, x0:x1]


def pose_metrics(detection: FaceDetection) -> dict[str, float]:
    """Estimate roll, yaw, and pitch from five landmarks, not a 3-D pose model."""
    points = detection.landmarks
    eyes = points[:2][np.argsort(points[:2, 0])]
    mouths = points[3:5][np.argsort(points[3:5, 0])]
    eye_left, eye_right = eyes
    eye_average = eyes.mean(axis=0)
    mouth_average = mouths.mean(axis=0)
    nose = points[2]
    eye_vector = eye_right - eye_left
    eye_distance = max(float(np.linalg.norm(eye_vector)), 1e-6)
    roll = float(np.degrees(np.arctan2(eye_vector[1], eye_vector[0])))
    yaw = float((nose[0] - eye_average[0]) / eye_distance)
    eye_to_mouth = mouth_average - eye_average
    denominator = max(float(np.dot(eye_to_mouth, eye_to_mouth)), 1e-6)
    pitch = float(np.dot(nose - eye_average, eye_to_mouth) / denominator)
    return {"roll_degrees": roll, "yaw_proxy": yaw, "pitch_proxy": pitch}


def assess_source_quality(
    image: np.ndarray,
    detection: FaceDetection,
    config: QualityConfig = QualityConfig(),
) -> QualityAssessment:
    """Return issue flags and metrics measured on the original photo.

    ``preprocess_image`` rejects on any issue before alignment or tensor
    creation. Exposure and blur are measured inside the detected face crop.
    """

    height, width = image.shape[:2]
    _, _, face_width, face_height = detection.bbox
    face_ratio = min(face_width / width, face_height / height)
    crop = _face_crop(image, detection)
    issues: list[str] = []
    if width < config.minimum_width or height < config.minimum_height:
        issues.append("resolution_too_low")
    if min(face_width, face_height) < config.minimum_face_pixels:
        issues.append("face_too_small_pixels")
    if face_ratio < config.minimum_face_ratio:
        issues.append("face_too_small_ratio")
    if detection.confidence < config.minimum_landmark_confidence:
        issues.append("landmark_confidence_too_low")

    if crop.size:
        grayscale = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        mean_luma = float(grayscale.mean())
        dark_ratio = float(np.mean(grayscale <= 10))
        bright_ratio = float(np.mean(grayscale >= 245))
        blur_variance = float(cv2.Laplacian(grayscale, cv2.CV_64F).var())
    else:
        mean_luma = dark_ratio = bright_ratio = blur_variance = 0.0
        issues.append("invalid_face_bounds")
    if mean_luma < config.minimum_luma:
        issues.append("exposure_too_dark")
    if mean_luma > config.maximum_luma:
        issues.append("exposure_too_bright")
    if dark_ratio > config.maximum_clipped_ratio:
        issues.append("dark_clipping_excessive")
    if bright_ratio > config.maximum_clipped_ratio:
        issues.append("bright_clipping_excessive")
    if blur_variance < config.minimum_laplacian_variance:
        issues.append("image_too_blurry")

    pose = pose_metrics(detection)
    if abs(pose["roll_degrees"]) > config.maximum_roll_degrees:
        issues.append("pose_roll_excessive")
    if abs(pose["yaw_proxy"]) > config.maximum_yaw_proxy:
        issues.append("pose_yaw_excessive")
    if not config.minimum_pitch_proxy <= pose["pitch_proxy"] <= config.maximum_pitch_proxy:
        issues.append("pose_pitch_excessive")

    metrics: dict[str, float | int] = {
        "input_width": width,
        "input_height": height,
        "face_width": float(face_width),
        "face_height": float(face_height),
        "face_ratio": float(face_ratio),
        "landmark_confidence": float(detection.confidence),
        "mean_luma": mean_luma,
        "dark_clipped_ratio": dark_ratio,
        "bright_clipped_ratio": bright_ratio,
        "laplacian_variance": blur_variance,
        **pose,
    }
    return QualityAssessment(not issues, tuple(issues), metrics)


def assess_face_mask(
    face_mask: np.ndarray,
    config: QualityConfig = QualityConfig(),
) -> QualityAssessment:
    """Reject implausibly small or large parsed face areas after alignment."""
    ratio = float(np.mean(face_mask.astype(bool)))
    issues: list[str] = []
    if ratio < config.minimum_face_mask_ratio:
        issues.append("face_parsing_area_too_small")
    if ratio > config.maximum_face_mask_ratio:
        issues.append("face_parsing_area_too_large")
    return QualityAssessment(not issues, tuple(issues), {"face_mask_ratio": ratio})


def quality_config_dict(config: QualityConfig) -> dict[str, object]:
    return asdict(config)
