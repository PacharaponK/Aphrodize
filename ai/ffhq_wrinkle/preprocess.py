"""End-to-end preprocessing for one user-provided face image."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageOps

from .alignment import ALIGNMENT_SIZE, FaceDetection, YuNetFaceDetector, align_face
from .face_parsing import (
    face_mask_from_labels,
    load_bisenet,
    mask_rgb_image,
    parse_face,
)
from .quality import (
    QualityAssessment,
    QualityConfig,
    QualityGateError,
    assess_face_mask,
    assess_source_quality,
    quality_config_dict,
)
from .paths import MODEL_ROOT
from .texture_map import PREPROCESSING_VERSION as TEXTURE_VERSION
from .texture_map import generate_texture_map

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
PREPROCESSING_VERSION = f"ffhq-user-image-v1+{TEXTURE_VERSION}"
MANAGED_ARTIFACTS = (
    "aligned_face.png",
    "face_mask.png",
    "masked_face.png",
    "texture_map.png",
    "model_input.npy",
)


@dataclass(frozen=True)
class PreprocessResult:
    tensor: np.ndarray
    aligned_face: np.ndarray
    face_mask: np.ndarray
    masked_face: np.ndarray
    texture_map: np.ndarray
    metadata: dict[str, object]


def load_user_image(path: str | Path) -> tuple[np.ndarray, str]:
    """Load JPEG, PNG, or WebP, applying EXIF orientation and RGB conversion."""

    path = Path(path)
    with Image.open(path) as opened:
        image_format = (opened.format or "").upper()
        if image_format not in SUPPORTED_FORMATS:
            raise ValueError(
                f"unsupported image format {image_format or 'unknown'}; "
                "expected JPEG, PNG, or WebP"
            )
        rgb = ImageOps.exif_transpose(opened).convert("RGB")
        return np.asarray(rgb, dtype=np.uint8), image_format


def build_four_channel_tensor(masked_face: np.ndarray, texture: np.ndarray) -> np.ndarray:
    """Return official RGB+texture CHW float32 data normalized to [-1, 1]."""

    if masked_face.ndim != 3 or masked_face.shape[2] != 3:
        raise ValueError("masked_face must be HxWx3")
    if texture.shape != masked_face.shape[:2]:
        raise ValueError("texture and RGB spatial sizes must match")
    combined = np.concatenate((masked_face, texture[:, :, None]), axis=2)
    return (combined.transpose(2, 0, 1).astype(np.float32) / 255.0) * 2.0 - 1.0


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reject(
    output_dir: Path,
    assessment: QualityAssessment,
    image_format: str,
    config: QualityConfig,
) -> None:
    # A rejected retry must not leave a model-ready tensor from an earlier run.
    for filename in MANAGED_ARTIFACTS:
        (output_dir / filename).unlink(missing_ok=True)
    _write_json(
        output_dir / "result.json",
        {
            "status": "rejected",
            "preprocessing_version": PREPROCESSING_VERSION,
            "input_format": image_format,
            "quality_flags": list(assessment.issues),
            "quality_metrics": assessment.metrics,
            "quality_thresholds": quality_config_dict(config),
            "model_input_created": False,
        },
    )
    raise QualityGateError(assessment)


def preprocess_image(
    image_path: str | Path,
    output_dir: str | Path,
    yunet_checkpoint: str | Path | None = None,
    bisenet_checkpoint: str | Path | None = None,
    *,
    detector=None,
    parser: Callable[[np.ndarray], np.ndarray] | None = None,
    quality_config: QualityConfig = QualityConfig(),
) -> PreprocessResult:
    """Validate and transform one image; rejected inputs never produce a tensor."""

    image_path = Path(image_path)
    output_dir = Path(output_dir)
    image, image_format = load_user_image(image_path)
    if detector is None:
        detector = YuNetFaceDetector(
            yunet_checkpoint or MODEL_ROOT / "face_detection_yunet_2023mar.onnx"
        )
    detections: list[FaceDetection] = detector.detect(image)
    if len(detections) != 1:
        issue = "no_face_detected" if not detections else "multiple_faces_detected"
        _reject(
            output_dir,
            QualityAssessment(False, (issue,), {"face_count": len(detections)}),
            image_format,
            quality_config,
        )
    detection = detections[0]
    source_quality = assess_source_quality(image, detection, quality_config)
    if not source_quality.passed:
        _reject(output_dir, source_quality, image_format, quality_config)

    aligned = align_face(image, detection, ALIGNMENT_SIZE)
    try:
        if parser is None:
            model = load_bisenet(
                bisenet_checkpoint or MODEL_ROOT / "79999_iter.pth", device="cpu"
            )
            labels = parse_face(aligned, model, device="cpu")
        else:
            labels = parser(aligned)
        face_mask = face_mask_from_labels(labels, aligned.shape[:2])
    except Exception as error:
        assessment = QualityAssessment(
            False,
            ("face_parsing_failed",),
            {"face_parsing_error": type(error).__name__},
        )
        _reject(output_dir, assessment, image_format, quality_config)

    parsing_quality = assess_face_mask(face_mask, quality_config)
    if not parsing_quality.passed:
        _reject(output_dir, parsing_quality, image_format, quality_config)

    masked_face = mask_rgb_image(aligned, face_mask)
    texture = generate_texture_map(aligned, face_mask)
    tensor = build_four_channel_tensor(masked_face, texture)

    output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(aligned, mode="RGB").save(output_dir / "aligned_face.png")
    Image.fromarray(face_mask.astype(np.uint8) * 255, mode="L").save(
        output_dir / "face_mask.png"
    )
    Image.fromarray(masked_face, mode="RGB").save(output_dir / "masked_face.png")
    Image.fromarray(texture, mode="L").save(output_dir / "texture_map.png")
    np.save(output_dir / "model_input.npy", tensor, allow_pickle=False)
    metrics = {**source_quality.metrics, **parsing_quality.metrics}
    metadata: dict[str, object] = {
        "status": "completed",
        "preprocessing_version": PREPROCESSING_VERSION,
        "input_format": image_format,
        "input_size": [int(image.shape[1]), int(image.shape[0])],
        "aligned_size": [ALIGNMENT_SIZE, ALIGNMENT_SIZE],
        "tensor_shape": list(tensor.shape),
        "tensor_dtype": str(tensor.dtype),
        "quality_flags": [],
        "quality_metrics": metrics,
        "quality_thresholds": quality_config_dict(quality_config),
        "model_input_created": True,
        "artifacts": {
            "aligned_face": "aligned_face.png",
            "face_mask": "face_mask.png",
            "masked_face": "masked_face.png",
            "texture_map": "texture_map.png",
            "model_input": "model_input.npy",
        },
    }
    _write_json(output_dir / "result.json", metadata)
    return PreprocessResult(tensor, aligned, face_mask, masked_face, texture, metadata)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--yunet-checkpoint", type=Path)
    parser.add_argument("--bisenet-checkpoint", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = preprocess_image(
            args.image,
            args.output,
            args.yunet_checkpoint,
            args.bisenet_checkpoint,
        )
    except QualityGateError as error:
        print(json.dumps({"status": "rejected", "quality_flags": error.assessment.issues}))
        return 2
    print(json.dumps(result.metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
