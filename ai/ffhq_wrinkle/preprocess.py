"""Convert one source photo into the four channels expected by Stage-2.

The path is decode -> detect one face -> quality checks -> align -> face
parsing -> masked RGB and texture. Rejected images never get a model tensor.
"""

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
    """In-memory model input and aligned-image arrays passed to prediction.

    ``tensor`` is ``[4,H,W]``; RGB arrays are ``[H,W,3]``; ``face_mask`` and
    ``texture_map`` are ``[H,W]``. Metadata names the saved artifacts.
    """
    tensor: np.ndarray
    aligned_face: np.ndarray
    face_mask: np.ndarray
    masked_face: np.ndarray
    texture_map: np.ndarray
    metadata: dict[str, object]


def load_user_image(path: str | Path) -> tuple[np.ndarray, str]:
    """Return RGB uint8 ``[H, W, 3]`` and format after EXIF correction."""

    # Accept either a string path or a Path object from the CLI/service.
    path = Path(path)
    # Pillow keeps the file open only while we decode and convert it.
    with Image.open(path) as opened:
        # The real encoded format matters more than the filename extension.
        image_format = (opened.format or "").upper()
        # Reject formats whose decoding and quality behavior this pipeline has not defined.
        if image_format not in SUPPORTED_FORMATS:
            raise ValueError(
                f"unsupported image format {image_format or 'unknown'}; "
                "expected JPEG, PNG, or WebP"
            )
        # Rotate according to camera EXIF, drop alpha if present, and force three RGB channels.
        rgb = ImageOps.exif_transpose(opened).convert("RGB")
        # NumPy now holds pixels in memory as unsigned 8-bit [height, width, RGB].
        return np.asarray(rgb, dtype=np.uint8), image_format


def build_four_channel_tensor(masked_face: np.ndarray, texture: np.ndarray) -> np.ndarray:
    """Stack masked RGB and texture as float32 ``[4, H, W]`` in ``[-1, 1]``.

The first three channels are face-only RGB; the fourth is the texture map.
``predict_image`` passes this array to PyTorch without rereading the NPY file.
    """

    # RGB must have one color triplet at every image coordinate.
    if masked_face.ndim != 3 or masked_face.shape[2] != 3:
        raise ValueError("masked_face must be HxWx3")
    # Texture supplies exactly one value for each RGB pixel.
    if texture.shape != masked_face.shape[:2]:
        raise ValueError("texture and RGB spatial sizes must match")
    # Add a singleton channel to texture, then append it after R, G, and B.
    combined = np.concatenate((masked_face, texture[:, :, None]), axis=2)
    # Move channels first for PyTorch and map byte values 0..255 to -1..1.
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
    # Keep the reason in result.json for a direct CLI caller inspecting output_dir.
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
    # The worker catches this typed error and records an image-quality rejection.
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
    """Prepare one model input and save inspectable intermediate artifacts.

    ``image_path`` is the service's temporary upload or a CLI input. On
    success, ``output_dir`` gets PNG/NPY files and a ``PreprocessResult`` is
    returned. On rejection, ``_reject`` writes flags to ``result.json`` and
    raises ``QualityGateError`` before a model-ready tensor is produced.
    """

    # Normalize both paths before any detector/model work begins.
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    # Decode the file into an in-memory RGB array; no new image file is written yet.
    image, image_format = load_user_image(image_path)
    # Detection runs on the source image so quality checks reflect the upload.
    if detector is None:
        # YuNet finds face boxes and landmarks in the original upload.
        detector = YuNetFaceDetector(
            yunet_checkpoint or MODEL_ROOT / "face_detection_yunet_2023mar.onnx"
        )
    detections: list[FaceDetection] = detector.detect(image)
    # Alignment and the score denominator need one unambiguous face.
    if len(detections) != 1:
        # Distinguish a missing face from a group photo in the rejection flags.
        issue = "no_face_detected" if not detections else "multiple_faces_detected"
        _reject(
            output_dir,
            QualityAssessment(False, (issue,), {"face_count": len(detections)}),
            image_format,
            quality_config,
        )
    # The sole detection includes landmarks used for alignment.
    detection = detections[0]
    # Check source resolution, face size, sharpness, pose, and other input criteria.
    source_quality = assess_source_quality(image, detection, quality_config)
    # Stop before parsing or inference when the upload fails these checks.
    if not source_quality.passed:
        _reject(output_dir, source_quality, image_format, quality_config)

    # Warp/crop the detected face into the model's standard square coordinates.
    aligned = align_face(image, detection, ALIGNMENT_SIZE)
    try:
        # Face parsing runs on the aligned face, independently of wrinkle inference.
        if parser is None:
            # BiSeNet labels face parts; it does not predict wrinkles.
            model = load_bisenet(
                bisenet_checkpoint or MODEL_ROOT / "79999_iter.pth", device="cpu"
            )
            # BiSeNet assigns a face-part class at each pixel of its 512² output.
            labels = parse_face(aligned, model, device="cpu")
        else:
            # Tests and research callers may inject a compatible parser.
            labels = parser(aligned)
        # Resize class labels without blending them into invalid intermediate values.
        face_mask = face_mask_from_labels(labels, aligned.shape[:2])
    except Exception as error:
        # Parsing errors become a named quality failure instead of partial output.
        assessment = QualityAssessment(
            False,
            ("face_parsing_failed",),
            {"face_parsing_error": type(error).__name__},
        )
        _reject(output_dir, assessment, image_format, quality_config)

    # Reject a mask that is empty, implausibly small, or otherwise unusable.
    parsing_quality = assess_face_mask(face_mask, quality_config)
    if not parsing_quality.passed:
        _reject(output_dir, parsing_quality, image_format, quality_config)

    # Zero out pixels outside the allowed face area in the RGB channels.
    masked_face = mask_rgb_image(aligned, face_mask)
    # Compute the grayscale texture channel from the aligned face and mask.
    texture = generate_texture_map(aligned, face_mask)
    # The Stage-2 model expects masked RGB and texture as one four-channel tensor.
    tensor = build_four_channel_tensor(masked_face, texture)

    # Persist intermediate files so a human can inspect each transformation.
    output_dir.mkdir(parents=True, exist_ok=True)
    # These files explain the transformation; the next stage uses returned arrays.
    # Full aligned RGB face: shared coordinates for every later image artifact.
    Image.fromarray(aligned, mode="RGB").save(output_dir / "aligned_face.png")
    # White marks pixels kept for wrinkle inference; black is excluded.
    Image.fromarray(face_mask.astype(np.uint8) * 255, mode="L").save(
        output_dir / "face_mask.png"
    )
    # The three RGB model channels have zeroes outside the face mask.
    Image.fromarray(masked_face, mode="RGB").save(output_dir / "masked_face.png")
    # The fourth model channel is saved as a viewable grayscale image.
    Image.fromarray(texture, mode="L").save(output_dir / "texture_map.png")
    # This NPY is an inspectable copy; prediction uses `tensor` in memory.
    np.save(output_dir / "model_input.npy", tensor, allow_pickle=False)
    # Merge metrics measured before alignment and after semantic parsing.
    metrics = {**source_quality.metrics, **parsing_quality.metrics}
    # result.json records dimensions, quality checks, and artifact filenames.
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
    # Pass arrays directly to prediction, avoiding a second image/NPY decode.
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
