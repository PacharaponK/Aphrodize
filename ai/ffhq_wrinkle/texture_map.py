"""Research-faithful FFHQ-Wrinkle texture-map generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image

from .face_parsing import face_mask_from_labels, load_label_map

PREPROCESSING_VERSION = "ffhq-wrinkle-texture-v1-bt709-dark-floor"
GAUSSIAN_KERNEL_SIZE = 21
GAUSSIAN_SIGMA = 5.0

IntensityMethod = Literal[
    "opencv_gray",
    "opencv_bgr_on_rgb",
    "pillow_gray",
    "bt601_float",
    "bt709_float",
    "rgb_channels",
    "rgb_mean",
    "red",
    "green",
    "blue",
]
RoundingMethod = Literal["truncate", "round"]
BlurDtype = Literal["uint8", "float32"]
ResponseMode = Literal["clip", "absolute", "wrap", "dark_only_floor"]
ChannelReduction = Literal[
    "before_quantize",
    "after_quantize",
    "max_after_quantize",
    "mean_after_quantize",
]

BORDER_TYPES = {
    "reflect101": cv2.BORDER_REFLECT_101,
    "reflect": cv2.BORDER_REFLECT,
    "replicate": cv2.BORDER_REPLICATE,
    "constant": cv2.BORDER_CONSTANT,
}


@dataclass(frozen=True)
class TextureMapConfig:
    kernel_size: int = GAUSSIAN_KERNEL_SIZE
    sigma: float = GAUSSIAN_SIGMA
    # The paper fixes the kernel and sigma but not these numerical details.
    # These defaults produced the lowest MAE against 100 official weak maps.
    intensity_method: IntensityMethod = "bt709_float"
    blur_dtype: BlurDtype = "float32"
    border: str = "reflect101"
    rounding: RoundingMethod = "round"
    denominator_offset: float = 1.0
    response_mode: ResponseMode = "dark_only_floor"
    channel_reduction: ChannelReduction = "after_quantize"

    def validate(self) -> None:
        if self.kernel_size < 1 or self.kernel_size % 2 == 0:
            raise ValueError("kernel_size must be a positive odd integer")
        if self.sigma <= 0:
            raise ValueError("sigma must be positive")
        if self.border not in BORDER_TYPES:
            raise ValueError(f"unsupported border mode: {self.border}")
        if self.denominator_offset <= 0:
            raise ValueError("denominator_offset must be positive")


def rgb_to_intensity(image: np.ndarray, method: IntensityMethod = "opencv_gray") -> np.ndarray:
    """Convert an RGB uint8 image into the intensity image ``I``."""

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"expected an HxWx3 RGB image, got shape {image.shape}")
    if image.dtype != np.uint8:
        raise TypeError(f"expected uint8 RGB input, got {image.dtype}")
    if method == "opencv_gray":
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    if method == "opencv_bgr_on_rgb":
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if method == "pillow_gray":
        return np.asarray(Image.fromarray(image, mode="RGB").convert("L"))
    if method == "bt601_float":
        return np.tensordot(image.astype(np.float32), np.array([0.299, 0.587, 0.114], np.float32), axes=([2], [0]))
    if method == "bt709_float":
        return np.tensordot(image.astype(np.float32), np.array([0.2126, 0.7152, 0.0722], np.float32), axes=([2], [0]))
    if method == "rgb_channels":
        return image
    if method == "rgb_mean":
        return image.astype(np.float32).mean(axis=2)
    channel_index = {"red": 0, "green": 1, "blue": 2}.get(method)
    if channel_index is None:
        raise ValueError(f"unsupported intensity method: {method}")
    return image[:, :, channel_index]


def gaussian_intensity(intensity: np.ndarray, config: TextureMapConfig) -> np.ndarray:
    """Return ``I_G(sigma)`` using an explicit finite OpenCV kernel."""

    config.validate()
    blur_input = intensity.astype(config.blur_dtype, copy=False)
    return cv2.GaussianBlur(
        blur_input,
        (config.kernel_size, config.kernel_size),
        sigmaX=config.sigma,
        sigmaY=config.sigma,
        borderType=BORDER_TYPES[config.border],
    )


def texture_response(
    intensity: np.ndarray,
    blurred: np.ndarray,
    config: TextureMapConfig,
) -> np.ndarray:
    """Apply the paper equation and quantize the continuous response to uint8."""

    if intensity.shape != blurred.shape:
        raise ValueError("intensity and blurred images must have identical shapes")
    formula_intensity = intensity.astype(np.float32)
    if config.response_mode == "dark_only_floor":
        formula_intensity = np.minimum(formula_intensity, blurred.astype(np.float32))
    response = (
        1.0
        - formula_intensity
        / (config.denominator_offset + blurred.astype(np.float32))
    ) * 255.0
    if response.ndim == 3 and config.channel_reduction == "before_quantize":
        response = cv2.cvtColor(response, cv2.COLOR_RGB2GRAY)
    elif config.channel_reduction not in (
        "before_quantize",
        "after_quantize",
        "max_after_quantize",
        "mean_after_quantize",
    ):
        raise ValueError(f"unsupported channel reduction: {config.channel_reduction}")
    if config.response_mode == "absolute":
        response = np.abs(response)
    elif config.response_mode not in ("clip", "wrap", "dark_only_floor"):
        raise ValueError(f"unsupported response mode: {config.response_mode}")
    if config.response_mode != "wrap":
        response = np.clip(response, 0.0, 255.0)
    if config.rounding == "round":
        response = np.rint(response)
    elif config.rounding != "truncate":
        raise ValueError(f"unsupported rounding method: {config.rounding}")
    return response.astype(np.uint8)


def generate_texture_map(
    image: np.ndarray,
    face_mask: np.ndarray | None = None,
    config: TextureMapConfig = TextureMapConfig(),
) -> np.ndarray:
    """Generate a continuous grayscale texture map and optionally mask non-face pixels."""

    intensity = rgb_to_intensity(image, config.intensity_method)
    blurred = gaussian_intensity(intensity, config)
    texture = texture_response(intensity, blurred, config)
    if texture.ndim == 3:
        if config.channel_reduction == "max_after_quantize":
            texture = texture.max(axis=2)
        elif config.channel_reduction == "mean_after_quantize":
            texture = np.rint(texture.astype(np.float32).mean(axis=2)).astype(np.uint8)
        else:
            texture = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)
    if face_mask is not None:
        if face_mask.shape != texture.shape:
            raise ValueError(
                f"mask shape {face_mask.shape} does not match texture shape {texture.shape}"
            )
        texture = texture.copy()
        texture[~face_mask.astype(bool)] = 0
    return texture


def generate_from_files(
    image_path: str | Path,
    parsing_labels_path: str | Path,
    output_path: str | Path,
    config: TextureMapConfig = TextureMapConfig(),
    debug_dir: str | Path | None = None,
) -> np.ndarray:
    """Generate and save the masked map, with optional intermediate artifacts."""

    image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
    labels = load_label_map(parsing_labels_path)
    face_mask = face_mask_from_labels(labels, image.shape[:2])
    intensity = rgb_to_intensity(image, config.intensity_method)
    blurred = gaussian_intensity(intensity, config)
    texture = texture_response(intensity, blurred, config)
    if texture.ndim == 3:
        if config.channel_reduction == "max_after_quantize":
            texture = texture.max(axis=2)
        elif config.channel_reduction == "mean_after_quantize":
            texture = np.rint(texture.astype(np.float32).mean(axis=2)).astype(np.uint8)
        else:
            texture = cv2.cvtColor(texture, cv2.COLOR_RGB2GRAY)
    masked = texture.copy()
    masked[~face_mask] = 0

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(masked, mode="L").save(output)

    if debug_dir is not None:
        debug = Path(debug_dir)
        debug.mkdir(parents=True, exist_ok=True)
        intermediate_mode = "RGB" if intensity.ndim == 3 else "L"
        Image.fromarray(np.asarray(intensity, dtype=np.uint8), mode=intermediate_mode).save(debug / "intensity.png")
        Image.fromarray(np.asarray(blurred, dtype=np.uint8), mode=intermediate_mode).save(debug / "gaussian.png")
        Image.fromarray(texture, mode="L").save(debug / "texture_unmasked.png")
        Image.fromarray(face_mask.astype(np.uint8) * 255, mode="L").save(debug / "face_mask.png")
    return masked


def build_parser():
    """Build the command-line parser without importing CLI dependencies at import time."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="aligned 1024x1024 RGB image")
    parser.add_argument("labels", type=Path, help="512x512 BiSeNet NPY label map")
    parser.add_argument("output", type=Path, help="output grayscale PNG")
    parser.add_argument("--debug-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    generate_from_files(args.image, args.labels, args.output, debug_dir=args.debug_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
