"""Resolve a manually approved model; no training job can activate itself."""

import json
import re
from pathlib import Path

from ai.ffhq_wrinkle.paths import MODEL_ROOT
from backend.services.curated_training import PREPROCESSING_VERSION, sha256_file


def approved_checkpoint(manifest_path: str | Path) -> Path:
    # Deployment uses only a manually approved manifest with a matching checkpoint hash.
    manifest = Path(manifest_path).resolve()
    # A manifest outside the mounted model tree cannot select a checkpoint.
    if not manifest.is_relative_to(MODEL_ROOT.resolve()):
        raise ValueError("approved model manifest must be inside the model directory")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    # Require approval, matching model architecture/preprocessing, and rights records.
    if (
        not isinstance(data, dict)
        or data.get("status") != "approved"
        or data.get("architecture") != "UNet"
        or data.get("preprocessing_version") != PREPROCESSING_VERSION
        or not data.get("approval_reference")
        or not data.get("rights_reference")
        or not re.fullmatch(r"[0-9a-f]{64}", str(data.get("checkpoint_sha256", "")))
    ):
        raise ValueError("model approval, rights, or preprocessing contract is missing")
    name = data.get("checkpoint")
    # Accept a simple local filename rather than a path into another directory.
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+\.pth", name):
        raise ValueError("invalid checkpoint filename")
    checkpoint = (manifest.parent / name).resolve()
    # Detect missing, moved, or modified checkpoint bytes before model loading.
    if (
        not checkpoint.is_relative_to(manifest.parent)
        or not checkpoint.is_file()
        or sha256_file(checkpoint) != data["checkpoint_sha256"]
    ):
        raise ValueError("approved checkpoint checksum mismatch")
    return checkpoint
