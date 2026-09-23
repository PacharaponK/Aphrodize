"""Face-region masking compatible with the FFHQ-Wrinkle preprocessing scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .bisenet import BiSeNet
from .paths import MODEL_ROOT

# CelebAMask-HQ / face-parsing.PyTorch labels used by the upstream script.
FACE_SKIN_LABEL = 1
NOSE_LABEL = 10
DEFAULT_FACE_LABELS = (FACE_SKIN_LABEL, NOSE_LABEL)
PARSING_INPUT_SIZE = (512, 512)
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def load_label_map(path: str | Path) -> np.ndarray:
    """Load an integer face-parsing label map from an NPY artifact."""

    labels = np.load(Path(path), allow_pickle=False)
    if labels.ndim != 2:
        raise ValueError(f"expected a 2D label map, got shape {labels.shape}")
    if not np.issubdtype(labels.dtype, np.integer):
        raise TypeError(f"expected integer labels, got {labels.dtype}")
    return labels


def resize_label_map(labels: np.ndarray, output_size: tuple[int, int]) -> np.ndarray:
    """Resize discrete labels with nearest-neighbor interpolation.

    ``output_size`` is expressed as ``(height, width)`` while OpenCV expects
    ``(width, height)``.
    """

    if labels.ndim != 2:
        raise ValueError(f"expected a 2D label map, got shape {labels.shape}")
    height, width = output_size
    if height < 1 or width < 1:
        raise ValueError("output dimensions must be positive")
    if labels.shape == (height, width):
        return labels.copy()
    resized = cv2.resize(labels, (width, height), interpolation=cv2.INTER_NEAREST)
    return resized.astype(labels.dtype, copy=False)


def face_mask_from_labels(
    labels: np.ndarray,
    output_size: tuple[int, int] | None = None,
    keep_labels: Iterable[int] = DEFAULT_FACE_LABELS,
) -> np.ndarray:
    """Return the boolean skin-and-nose mask used by FFHQ-Wrinkle."""

    if output_size is not None:
        labels = resize_label_map(labels, output_size)
    keep = tuple(int(label) for label in keep_labels)
    if not keep:
        raise ValueError("keep_labels must contain at least one label")
    return np.isin(labels, keep)


def mask_rgb_image(image: np.ndarray, face_mask: np.ndarray) -> np.ndarray:
    """Set non-face RGB pixels to zero without changing image dtype."""

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"expected an HxWx3 RGB image, got shape {image.shape}")
    if face_mask.shape != image.shape[:2]:
        raise ValueError(
            f"mask shape {face_mask.shape} does not match image shape {image.shape[:2]}"
        )
    result = image.copy()
    result[~face_mask.astype(bool)] = 0
    return result


def load_bisenet(checkpoint_path: str | Path, device: str = "cpu"):
    """Load the 19-class face-parsing BiSeNet from an upstream checkpoint."""

    import torch

    checkpoint = Path(checkpoint_path)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"BiSeNet checkpoint not found: {checkpoint}")
    model = BiSeNet(n_classes=19)
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    if not isinstance(state, dict):
        raise TypeError("BiSeNet checkpoint must contain a state dictionary")
    if state and all(str(key).startswith("module.") for key in state):
        state = {str(key)[7:]: value for key, value in state.items()}
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model


def parse_face(image: np.ndarray, model, device: str = "cpu") -> np.ndarray:
    """Run BiSeNet and return a 512x512 CelebAMask-HQ integer label map.

    The resize and ImageNet normalization reproduce the upstream evaluator.
    Discrete labels should subsequently be enlarged with
    :func:`resize_label_map`, which always uses nearest-neighbor interpolation.
    """

    import torch
    from PIL import Image

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"expected an HxWx3 RGB image, got shape {image.shape}")
    if image.dtype != np.uint8:
        raise TypeError(f"expected uint8 RGB input, got {image.dtype}")
    # Pillow bilinear is intentional: it is what the upstream evaluator uses.
    resized = np.asarray(
        Image.fromarray(image, mode="RGB").resize(
            PARSING_INPUT_SIZE[::-1], Image.Resampling.BILINEAR
        )
    )
    tensor = torch.from_numpy(resized.astype(np.float32) / 255.0).permute(2, 0, 1)
    mean = torch.tensor(IMAGENET_MEAN, dtype=tensor.dtype).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD, dtype=tensor.dtype).view(3, 1, 1)
    tensor = ((tensor - mean) / std).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits = model(tensor)[0]
    return logits.squeeze(0).argmax(0).cpu().numpy().astype(np.uint8)


def parse_face_file(
    image_path: str | Path,
    checkpoint_path: str | Path,
    output_path: str | Path,
    device: str = "cpu",
) -> np.ndarray:
    """Parse one image with BiSeNet and save its raw 512x512 NPY labels."""

    from PIL import Image

    image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
    labels = parse_face(image, load_bisenet(checkpoint_path, device), device)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, labels, allow_pickle=False)
    return labels


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=MODEL_ROOT / "79999_iter.pth",
    )
    parser.add_argument("--device", default="cpu")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    parse_face_file(args.image, args.checkpoint, args.output, args.device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
