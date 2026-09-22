"""Verify the FFHQ-Wrinkle Phase 0 environment and checkpoint baseline."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import sys
import tempfile
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

from .reproducibility import DEFAULT_SEED, seed_everything

PACKAGE_DIR = Path(__file__).resolve().parent
AI_DIR = PACKAGE_DIR.parent
DATA_DIR = AI_DIR / "ffhq-wrinkle"
DEFAULT_MANIFEST = PACKAGE_DIR / "checkpoints.sha256"
DEFAULT_ARCHIVE = DATA_DIR / "pretrained_ckpt" / "checkpoints.zip"

IMPORTS = {
    "numpy": "numpy",
    "torch": "torch",
    "torchvision": "torchvision",
    "tqdm": "tqdm",
    "typing_extensions": "typing_extensions",
    "yacs": "yacs",
    "einops": "einops",
    "monai": "monai",
    "Pillow": "PIL",
}

STAGE2_MEMBERS = {
    "UNet": "stage2_wrinkle_finetune_unet/stage2_unet.pth",
    "SwinUNETR": "stage2_wrinkle_finetune_swinunetr/stage2_swinunetr.pth",
}


def parse_manifest(path: Path) -> dict[str, tuple[str, int]]:
    entries: dict[str, tuple[str, int]] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            raise ValueError(f"invalid manifest line {line_number}: {raw_line!r}")
        digest, size, item_path = parts
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid SHA-256 on manifest line {line_number}")
        entries[item_path] = (digest, int(size))
    return entries


def _hash_stream(stream: Any) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def verify_checkpoints(archive_path: Path, manifest_path: Path) -> dict[str, Any]:
    entries = parse_manifest(manifest_path)
    archive_key = "pretrained_ckpt/checkpoints.zip"
    expected_archive_hash, expected_archive_size = entries[archive_key]
    actual_archive_size = archive_path.stat().st_size
    with archive_path.open("rb") as stream:
        actual_archive_hash = _hash_stream(stream)

    results: dict[str, Any] = {
        "archive": {
            "path": str(archive_path),
            "bytes": actual_archive_size,
            "sha256": actual_archive_hash,
            "ok": actual_archive_size == expected_archive_size
            and actual_archive_hash == expected_archive_hash,
        },
        "members": [],
    }

    with zipfile.ZipFile(archive_path) as archive:
        for item_path, (expected_hash, expected_size) in entries.items():
            prefix = f"{archive_key}::"
            if not item_path.startswith(prefix):
                continue
            member_name = item_path.removeprefix(prefix)
            info = archive.getinfo(member_name)
            with archive.open(info) as stream:
                actual_hash = _hash_stream(stream)
            results["members"].append(
                {
                    "path": member_name,
                    "bytes": info.file_size,
                    "sha256": actual_hash,
                    "ok": info.file_size == expected_size and actual_hash == expected_hash,
                }
            )

    results["ok"] = results["archive"]["ok"] and all(
        member["ok"] for member in results["members"]
    )
    return results


def inspect_environment(requested_device: str) -> dict[str, Any]:
    dependencies: dict[str, Any] = {}
    loaded: dict[str, Any] = {}
    for package_name, module_name in IMPORTS.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # Report binary/import compatibility failures too.
            dependencies[package_name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        else:
            loaded[module_name] = module
            dependencies[package_name] = {
                "ok": True,
                "version": getattr(module, "__version__", "unknown"),
            }

    report: dict[str, Any] = {
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "dependencies": dependencies,
        "requested_device": requested_device,
        "selected_device": None,
        "cuda": {"available": False, "devices": []},
    }

    torch = loaded.get("torch")
    if torch is None:
        report["error"] = "PyTorch is unavailable"
        report["ok"] = False
        return report

    cuda_available = bool(torch.cuda.is_available())
    report["cuda"]["available"] = cuda_available
    report["cuda"]["runtime_version"] = torch.version.cuda
    if cuda_available:
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            report["cuda"]["devices"].append(
                {
                    "index": index,
                    "name": properties.name,
                    "total_memory_bytes": properties.total_memory,
                    "total_memory_gib": round(properties.total_memory / 1024**3, 2),
                }
            )

    if requested_device == "cuda" and not cuda_available:
        report["error"] = "CUDA was explicitly requested but is unavailable"
    else:
        report["selected_device"] = (
            "cuda" if requested_device == "cuda" or (requested_device == "auto" and cuda_available) else "cpu"
        )

    report["ok"] = all(item["ok"] for item in dependencies.values()) and "error" not in report
    return report


def _normalized_state_dict(checkpoint: Any) -> OrderedDict[str, Any]:
    state_dict = checkpoint["model"] if isinstance(checkpoint, dict) and "model" in checkpoint else checkpoint
    return OrderedDict(
        (key[7:] if key.startswith("module.") else key, value)
        for key, value in state_dict.items()
    )


def verify_strict_model_loading(archive_path: Path, official_repo: Path) -> dict[str, Any]:
    """Strict-load both Stage-2 models using definitions from the pinned upstream checkout."""

    if not (official_repo / "unet" / "unet_model.py").is_file():
        raise FileNotFoundError(f"official model definitions not found under {official_repo}")

    sys.path.insert(0, str(official_repo))
    try:
        import torch
        from unet.swin_unetr import SwinUNETR
        from unet.unet_model import UNet

        constructors = {
            "UNet": lambda: UNet(n_channels=4, n_classes=2, bilinear=True),
            "SwinUNETR": lambda: SwinUNETR(in_channels=4, out_channels=2),
        }
        output: dict[str, Any] = {}
        with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for architecture, member_name in STAGE2_MEMBERS.items():
                checkpoint_path = temp_root / Path(member_name).name
                with archive.open(member_name) as source, checkpoint_path.open("wb") as destination:
                    while chunk := source.read(1024 * 1024):
                        destination.write(chunk)
                try:
                    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
                except TypeError:  # Compatibility with a future/older torch API.
                    checkpoint = torch.load(checkpoint_path, map_location="cpu")
                model = constructors[architecture]()
                incompatible = model.load_state_dict(_normalized_state_dict(checkpoint), strict=True)
                output[architecture] = {
                    "ok": not incompatible.missing_keys and not incompatible.unexpected_keys,
                    "missing_keys": incompatible.missing_keys,
                    "unexpected_keys": incompatible.unexpected_keys,
                    "checkpoint": member_name,
                }
                del checkpoint, model
        output["ok"] = all(item["ok"] for item in output.values())
        return output
    finally:
        sys.path.remove(str(official_repo))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--official-repo",
        type=Path,
        help="Pinned official checkout; enables strict Stage-2 U-Net and SwinUNETR loading",
    )
    parser.add_argument("--skip-checksums", action="store_true", help="Skip the large archive hash pass")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report: dict[str, Any] = {
        "seed": seed_everything(args.seed),
        "environment": inspect_environment(args.device),
    }
    if not args.skip_checksums:
        try:
            report["checkpoints"] = verify_checkpoints(args.archive, args.manifest)
        except Exception as exc:
            report["checkpoints"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if args.official_repo:
        try:
            report["model_loading"] = verify_strict_model_loading(args.archive, args.official_repo.resolve())
        except Exception as exc:
            report["model_loading"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    required_sections = ["environment"]
    if not args.skip_checksums:
        required_sections.append("checkpoints")
    if args.official_repo:
        required_sections.append("model_loading")
    report["ok"] = all(report[section].get("ok", False) for section in required_sections)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

