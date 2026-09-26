"""Run Stage-2 wrinkle segmentation on a preprocessed four-channel image.

The model produces two logits channels. Class 1 is converted to a probability
map, thresholded inside the face mask, and visualized as a mask and overlay.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable

import numpy as np
import torch
from PIL import Image

from .modeling import ModelBundle, load_wrinkle_model
from .preprocess import PREPROCESSING_VERSION, PreprocessResult, preprocess_image

THRESHOLD_VERSION = "softmax-class1-face-mask-v1"
PREDICTION_VERSION = "ffhq-wrinkle-inference-v1"


@dataclass(frozen=True)
class ThresholdConfig:
    probability: float = 0.5
    positive_class: int = 1
    version: str = THRESHOLD_VERSION

    def validate(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability threshold must be within [0, 1]")
        if self.positive_class != 1:
            raise ValueError("official two-class checkpoints use wrinkle class index 1")
        if not self.version:
            raise ValueError("threshold version must not be empty")


@dataclass(frozen=True)
class PredictionResult:
    """In-memory model output returned to the application service.

    Logits are ``[2,H,W]``; probability and mask are ``[H,W]``; overlay is
    RGB ``[H,W,3]``. The service scores these arrays without reading NPYs.
    """
    logits: np.ndarray
    probability: np.ndarray
    mask: np.ndarray
    overlay: np.ndarray
    metadata: dict[str, object]


def ensure_output_available(output_dir: Path, overwrite: bool = False) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"output directory is not empty: {output_dir}; use --overwrite to replace "
            "managed artifacts explicitly"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        print(f"warning: overwriting managed artifacts in {output_dir}", file=sys.stderr)


def infer_logits_and_probability(
    model: torch.nn.Module,
    tensor: np.ndarray,
    device: torch.device,
    positive_class: int = 1,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return ``[2,H,W]`` logits and ``[H,W]`` class-1 probability.

    PyTorch receives a batch-shaped ``[1,4,H,W]`` tensor. No gradients are
    needed because this path only performs inference.
    """

    if tensor.shape[0] != 4 or tensor.ndim != 3:
        raise ValueError("model input must have shape (4, height, width)")
    inputs = torch.from_numpy(np.ascontiguousarray(tensor)).unsqueeze(0).to(device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    started = perf_counter()
    with torch.inference_mode():
        output = model(inputs)
        if output.ndim != 4 or output.shape[0] != 1 or output.shape[1] != 2:
            raise ValueError(f"model must return [1, 2, H, W] logits, got {tuple(output.shape)}")
        probability = torch.softmax(output, dim=1)[0, positive_class]
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elapsed = perf_counter() - started
    return (
        output[0].detach().cpu().numpy().astype(np.float32, copy=False),
        probability.detach().cpu().numpy().astype(np.float32, copy=False),
        elapsed,
    )


def threshold_probability(
    probability: np.ndarray,
    face_mask: np.ndarray,
    config: ThresholdConfig = ThresholdConfig(),
) -> np.ndarray:
    """Keep pixels above the probability threshold only inside the face."""
    config.validate()
    if probability.shape != face_mask.shape:
        raise ValueError("probability and face mask shapes must match")
    return (probability >= config.probability) & face_mask.astype(bool)


def create_overlay(
    aligned_face: np.ndarray,
    wrinkle_mask: np.ndarray,
    alpha: float = 0.55,
) -> np.ndarray:
    """Tint detected wrinkle pixels red on the aligned RGB face."""
    if aligned_face.shape[:2] != wrinkle_mask.shape:
        raise ValueError("aligned face and wrinkle mask shapes must match")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("overlay alpha must be within [0, 1]")
    overlay = aligned_face.astype(np.float32).copy()
    color = np.array([255.0, 32.0, 32.0], dtype=np.float32)
    selected = wrinkle_mask.astype(bool)
    overlay[selected] = overlay[selected] * (1.0 - alpha) + color * alpha
    return np.rint(np.clip(overlay, 0, 255)).astype(np.uint8)


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def predict_image(
    image_path: str | Path,
    output_dir: str | Path,
    architecture: str = "UNet",
    checkpoint_path: str | Path | None = None,
    requested_device: str = "auto",
    threshold: ThresholdConfig = ThresholdConfig(),
    *,
    overwrite: bool = False,
    model_bundle: ModelBundle | None = None,
    preprocessor: Callable[..., PreprocessResult] = preprocess_image,
    preprocess_kwargs: dict[str, object] | None = None,
) -> PredictionResult:
    """Run preprocess -> model -> postprocess and return arrays plus metadata.

    With a service-provided ``model_bundle`` the model is already loaded.
    Direct CLI calls preprocess first and load the checkpoint afterward.
    The saved NPY/PNG files aid inspection; later steps use returned arrays.
    """

    threshold.validate()
    output = Path(output_dir)
    ensure_output_available(output, overwrite)
    total_started = perf_counter()
    preprocessing_started = perf_counter()
    # image_path is the input photo; output is the directory for intermediate files.
    prepared = preprocessor(
        image_path,
        output,
        **(preprocess_kwargs or {}),
    )
    preprocessing_seconds = perf_counter() - preprocessing_started

    if model_bundle is None:
        # CLI calls reach this branch; the service supplies its cached bundle.
        bundle = load_wrinkle_model(architecture, checkpoint_path, requested_device)
    else:
        bundle = model_bundle
        if bundle.architecture.lower() != architecture.lower():
            raise ValueError(
                f"provided model bundle is {bundle.architecture}, requested {architecture}"
            )
    logits, probability, inference_seconds = infer_logits_and_probability(
        bundle.model, prepared.tensor, bundle.device, threshold.positive_class
    )
    # Both the displayed mask and later scores must stay within parsed face skin.
    postprocess_started = perf_counter()
    mask = threshold_probability(probability, prepared.face_mask, threshold)
    overlay = create_overlay(prepared.aligned_face, mask)
    # Persist research artifacts for CLI runs; the service removes its temporary copy.
    np.save(output / "wrinkle_logits.npy", logits, allow_pickle=False)
    np.save(output / "wrinkle_probability.npy", probability, allow_pickle=False)
    probability_png = np.rint(np.clip(probability, 0.0, 1.0) * 255.0).astype(np.uint8)
    Image.fromarray(probability_png, mode="L").save(output / "wrinkle_probability.png")
    Image.fromarray(mask.astype(np.uint8) * 255, mode="L").save(output / "wrinkle_mask.png")
    Image.fromarray(overlay, mode="RGB").save(output / "overlay.png")
    postprocess_seconds = perf_counter() - postprocess_started
    face_pixels = int(np.count_nonzero(prepared.face_mask))
    wrinkle_pixels = int(np.count_nonzero(mask))
    metadata: dict[str, object] = {
        "status": "completed",
        "prediction_version": PREDICTION_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "model": {
            "architecture": bundle.architecture,
            "checkpoint": str(bundle.checkpoint),
            "checkpoint_sha256": bundle.checkpoint_sha256,
            "output_classes": 2,
            "wrinkle_class_index": threshold.positive_class,
        },
        "threshold": asdict(threshold),
        "device": bundle.device_metadata,
        "input_size": prepared.metadata.get("input_size"),
        "aligned_size": prepared.metadata.get("aligned_size"),
        "quality_flags": prepared.metadata.get("quality_flags", []),
        "quality_metrics": prepared.metadata.get("quality_metrics", {}),
        "wrinkle_pixels": wrinkle_pixels,
        "face_pixels": face_pixels,
        "wrinkle_area_ratio": wrinkle_pixels / face_pixels if face_pixels else 0.0,
        "wrinkle_image_ratio": wrinkle_pixels / mask.size,
        "latency_seconds": {
            "preprocessing": preprocessing_seconds,
            "model_loading": bundle.load_seconds,
            "inference": inference_seconds,
            "postprocessing_and_save": postprocess_seconds,
            "total": perf_counter() - total_started,
        },
        "output_overwrite": overwrite,
        "artifacts": {
            **prepared.metadata.get("artifacts", {}),
            "logits": "wrinkle_logits.npy",
            "probability_raw": "wrinkle_probability.npy",
            "probability": "wrinkle_probability.png",
            "mask": "wrinkle_mask.png",
            "overlay": "overlay.png",
        },
    }
    _write_json(output / "result.json", metadata)
    return PredictionResult(logits, probability, mask, overlay, metadata)
