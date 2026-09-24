"""Download and verify the pinned OpenCV YuNet face-detector model."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import cv2
import requests

from ai.ffhq_wrinkle.paths import MODEL_ROOT

OPENCV_ZOO_COMMIT = "47534e27c9851bb1128ccc0102f1145e27f23f98"
YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
YUNET_URL = (
    "https://raw.githubusercontent.com/opencv/opencv_zoo/"
    f"{OPENCV_ZOO_COMMIT}/models/face_detection_yunet/{YUNET_FILENAME}"
)
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
YUNET_BYTES = 232_589


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(path: Path) -> None:
    if path.stat().st_size != YUNET_BYTES:
        raise ValueError(f"YuNet size mismatch: {path.stat().st_size} != {YUNET_BYTES}")
    actual = sha256_file(path)
    if actual != YUNET_SHA256:
        raise ValueError(f"YuNet SHA-256 mismatch: {actual} != {YUNET_SHA256}")
    # Parsing the ONNX model catches structurally invalid files beyond checksum.
    cv2.FaceDetectorYN.create(str(path), "", (320, 320), 0.6, 0.3, 5000)


def download_model(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        verify_model(destination)
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(YUNET_URL, stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for block in response.iter_content(1024 * 1024):
                    if block:
                        handle.write(block)
        verify_model(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=MODEL_ROOT / YUNET_FILENAME,
    )
    args = parser.parse_args()
    path = download_model(args.output)
    print(f"verified {path} sha256={YUNET_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
