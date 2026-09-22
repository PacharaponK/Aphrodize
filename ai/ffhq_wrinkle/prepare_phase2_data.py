"""Download and verify the upstream BiSeNet face-parsing checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import requests

BISENET_CHECKPOINT_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812&export=download&confirm=t"
)
BISENET_CHECKPOINT_SHA256 = (
    "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567"
)
BISENET_CHECKPOINT_BYTES = 53_289_463


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checkpoint(path: Path) -> None:
    if path.stat().st_size != BISENET_CHECKPOINT_BYTES:
        raise ValueError(
            f"BiSeNet checkpoint size mismatch: {path.stat().st_size} "
            f"!= {BISENET_CHECKPOINT_BYTES}"
        )
    actual = sha256_file(path)
    if actual != BISENET_CHECKPOINT_SHA256:
        raise ValueError(
            f"BiSeNet checkpoint SHA-256 mismatch: {actual} "
            f"!= {BISENET_CHECKPOINT_SHA256}"
        )


def download_checkpoint(destination: Path) -> Path:
    """Download atomically, rejecting HTML/interstitials and corrupt content."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        verify_checkpoint(destination)
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(BISENET_CHECKPOINT_URL, stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for block in response.iter_content(1024 * 1024):
                    if block:
                        handle.write(block)
        verify_checkpoint(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    data_root = Path(__file__).resolve().parent.parent / "ffhq-wrinkle"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=data_root / "pretrained_ckpt" / "79999_iter.pth",
    )
    args = parser.parse_args()
    path = download_checkpoint(args.output)
    print(f"verified {path} sha256={BISENET_CHECKPOINT_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
