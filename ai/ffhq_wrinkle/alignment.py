"""Find one source-image face and map it to a fixed FFHQ coordinate system.

YuNet supplies a bounding box and five landmarks. The landmarks define the
oriented square that ``align_face`` warps to 1024 x 1024 pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

ALIGNMENT_SIZE = 1024


@dataclass(frozen=True)
class FaceDetection:
    """One face box and YuNet's five facial landmarks in image coordinates."""

    bbox: tuple[float, float, float, float]
    landmarks: np.ndarray
    confidence: float

    def __post_init__(self) -> None:
        points = np.asarray(self.landmarks, dtype=np.float32)
        if points.shape != (5, 2) or not np.isfinite(points).all():
            raise ValueError("landmarks must be a finite 5x2 array")
        if len(self.bbox) != 4 or not np.isfinite(self.bbox).all():
            raise ValueError("bbox must contain four finite values")
        object.__setattr__(self, "landmarks", points)


class YuNetFaceDetector:
    """OpenCV YuNet wrapper returning stable, confidence-sorted detections."""

    def __init__(
        self,
        model_path: str | Path,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        maximum_input_side: int = 1600,
    ) -> None:
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"YuNet model not found: {model_path}")
        self.score_threshold = float(score_threshold)
        self.maximum_input_side = int(maximum_input_side)
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path),
            "",
            (320, 320),
            self.score_threshold,
            float(nms_threshold),
            int(top_k),
        )

    def detect(self, image: np.ndarray) -> list[FaceDetection]:
        """Return source-coordinate detections, highest confidence first."""
        if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
            raise ValueError("YuNet expects an HxWx3 uint8 RGB image")
        height, width = image.shape[:2]
        # Bound detector cost while mapping boxes and landmarks back to source pixels.
        scale = min(1.0, self.maximum_input_side / max(height, width))
        if scale < 1.0:
            detector_image = cv2.resize(
                image,
                (round(width * scale), round(height * scale)),
                interpolation=cv2.INTER_AREA,
            )
        else:
            detector_image = image
        detector_height, detector_width = detector_image.shape[:2]
        self._detector.setInputSize((detector_width, detector_height))
        _, faces = self._detector.detect(
            cv2.cvtColor(detector_image, cv2.COLOR_RGB2BGR)
        )
        if faces is None:
            return []
        results: list[FaceDetection] = []
        inverse_scale = 1.0 / scale
        for row in faces:
            bbox = tuple(float(value * inverse_scale) for value in row[:4])
            landmarks = row[4:14].reshape(5, 2).astype(np.float32) * inverse_scale
            results.append(FaceDetection(bbox, landmarks, float(row[14])))
        return sorted(results, key=lambda item: item.confidence, reverse=True)


def ffhq_alignment_quad(
    detection: FaceDetection, scale: float = 1.0
) -> np.ndarray:
    """Use the eye and mouth landmarks to locate an oriented face square."""

    points = detection.landmarks
    eyes = points[:2][np.argsort(points[:2, 0])]
    mouth = points[3:5][np.argsort(points[3:5, 0])]
    eye_left, eye_right = eyes
    mouth_left, mouth_right = mouth
    eye_average = (eye_left + eye_right) * 0.5
    mouth_average = (mouth_left + mouth_right) * 0.5
    eye_to_eye = eye_right - eye_left
    eye_to_mouth = mouth_average - eye_average
    axis_x = eye_to_eye + np.array(
        [eye_to_mouth[1], -eye_to_mouth[0]], dtype=np.float32
    )
    norm = float(np.linalg.norm(axis_x))
    if norm < 1e-6:
        raise ValueError("degenerate facial landmarks cannot be aligned")
    axis_x /= norm
    axis_x *= max(
        float(np.linalg.norm(eye_to_eye)) * 2.0,
        float(np.linalg.norm(eye_to_mouth)) * 1.8,
    ) * float(scale)
    axis_y = np.array([-axis_x[1], axis_x[0]], dtype=np.float32)
    center = eye_average + eye_to_mouth * 0.1
    return np.stack(
        (
            center - axis_x - axis_y,
            center - axis_x + axis_y,
            center + axis_x + axis_y,
            center + axis_x - axis_y,
        )
    ).astype(np.float32)


def align_face(
    image: np.ndarray,
    detection: FaceDetection,
    output_size: int = ALIGNMENT_SIZE,
) -> np.ndarray:
    """Return aligned RGB uint8 ``[output_size, output_size, 3]``.

    The same face coordinates are used later for parsing, texture, wrinkle
    segmentation, region scores, and the displayed overlay.
    """

    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("alignment expects an HxWx3 uint8 RGB image")
    if output_size < 64:
        raise ValueError("output_size must be at least 64")
    source = ffhq_alignment_quad(detection)
    edge = float(output_size - 1)
    destination = np.array(
        [[0.0, 0.0], [0.0, edge], [edge, edge], [edge, 0.0]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(
        image,
        transform,
        (output_size, output_size),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
