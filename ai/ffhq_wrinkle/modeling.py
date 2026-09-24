"""Strict Stage-2 model loading and device selection for wrinkle inference."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import torch

from .official.unet.swin_unetr import SwinUNETR
from .official.unet.unet_model import UNet
from .paths import MODEL_ROOT

ARCHITECTURES = ("UNet", "SwinUNETR")
OFFICIAL_STAGE2 = {
    "UNet": {
        "relative_path": "stage2_wrinkle_finetune_unet/stage2_unet.pth",
        "sha256": "883034b3e0726dcdae946c312106dfde1d354ea5455fa21cba045a73058f4a25",
        "bytes": 207_296_760,
    },
    "SwinUNETR": {
        "relative_path": "stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth",
        "sha256": "b8f6a46c49d52f5725d0d79740d2c9508b4f8aa6400ea4fe0b27f7a6cd8bdd12",
        "bytes": 307_302_386,
    },
}


class CheckpointArchitectureError(RuntimeError):
    """Raised when a checkpoint cannot be loaded strictly into its named model."""


@dataclass(frozen=True)
class DeviceSelection:
    device: torch.device
    requested: str
    fallback_used: bool
    fallback_reason: str | None


@dataclass(frozen=True)
class ModelBundle:
    model: torch.nn.Module
    architecture: str
    checkpoint: Path
    checkpoint_sha256: str
    device: torch.device
    device_metadata: dict[str, object]
    load_seconds: float


def canonical_architecture(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {"unet": "UNet", "swinunetr": "SwinUNETR", "swin": "SwinUNETR"}
    if normalized not in mapping:
        raise ValueError(f"unsupported architecture {value!r}; choose UNet or SwinUNETR")
    return mapping[normalized]


def default_checkpoint(architecture: str) -> Path:
    architecture = canonical_architecture(architecture)
    return MODEL_ROOT / str(OFFICIAL_STAGE2[architecture]["relative_path"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_device(requested: str = "auto") -> DeviceSelection:
    requested = requested.lower()
    if requested not in ("auto", "cpu", "cuda"):
        raise ValueError("device must be auto, cpu, or cuda")
    cuda_available = bool(torch.cuda.is_available())
    if requested == "cpu":
        return DeviceSelection(torch.device("cpu"), requested, False, None)
    if cuda_available:
        return DeviceSelection(torch.device("cuda"), requested, False, None)
    reason = "CUDA is unavailable in the installed PyTorch build"
    if requested == "cuda":
        return DeviceSelection(torch.device("cpu"), requested, True, reason)
    return DeviceSelection(torch.device("cpu"), requested, False, None)


def device_metadata(selection: DeviceSelection) -> dict[str, object]:
    metadata: dict[str, object] = {
        "requested": selection.requested,
        "selected": selection.device.type,
        "fallback_used": selection.fallback_used,
        "fallback_reason": selection.fallback_reason,
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "torch_cuda_version": torch.version.cuda,
    }
    if selection.device.type == "cuda":
        index = selection.device.index or torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(index)
        metadata.update(
            {
                "cuda_device_index": index,
                "cuda_device_name": properties.name,
                "cuda_total_memory_bytes": properties.total_memory,
            }
        )
    return metadata


def create_model(architecture: str) -> torch.nn.Module:
    architecture = canonical_architecture(architecture)
    if architecture == "UNet":
        return UNet(n_channels=4, n_classes=2, bilinear=True)
    return SwinUNETR(in_channels=4, out_channels=2)


def load_checkpoint_strict(
    model: torch.nn.Module,
    checkpoint_path: str | Path,
    device: torch.device,
    architecture: str,
) -> torch.nn.Module:
    checkpoint_path = Path(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    state = checkpoint["model"] if isinstance(checkpoint, dict) and "model" in checkpoint else checkpoint
    if not isinstance(state, dict):
        raise CheckpointArchitectureError("checkpoint does not contain a state dictionary")
    normalized = OrderedDict(
        (str(key)[7:] if str(key).startswith("module.") else str(key), value)
        for key, value in state.items()
    )
    try:
        model.load_state_dict(normalized, strict=True)
    except RuntimeError as error:
        raise CheckpointArchitectureError(
            f"checkpoint is incompatible with {canonical_architecture(architecture)}: {error}"
        ) from error
    return model


def load_wrinkle_model(
    architecture: str,
    checkpoint_path: str | Path | None = None,
    requested_device: str = "auto",
    verify_official: bool = True,
) -> ModelBundle:
    """Create a model, verify its official Stage-2 artifact, and load strictly."""

    started = perf_counter()
    architecture = canonical_architecture(architecture)
    checkpoint = Path(checkpoint_path) if checkpoint_path else default_checkpoint(architecture)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Stage-2 checkpoint not found: {checkpoint}")
    actual_size = checkpoint.stat().st_size
    actual_sha256 = sha256_file(checkpoint)
    if verify_official:
        expected = OFFICIAL_STAGE2[architecture]
        if actual_size != expected["bytes"] or actual_sha256 != expected["sha256"]:
            raise CheckpointArchitectureError(
                f"checkpoint does not match official Stage-2 {architecture} artifact"
            )
    selection = resolve_device(requested_device)
    model = create_model(architecture).to(selection.device)
    load_checkpoint_strict(model, checkpoint, selection.device, architecture)
    model.eval()
    return ModelBundle(
        model=model,
        architecture=architecture,
        checkpoint=checkpoint.resolve(),
        checkpoint_sha256=actual_sha256,
        device=selection.device,
        device_metadata=device_metadata(selection),
        load_seconds=perf_counter() - started,
    )
