"""Train a candidate wrinkle model from an explicitly approved external dataset."""

import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

APPROVED_DATA_ROOT = Path(__file__).resolve().parents[2] / "storage/data/approved"
DATASET_URI = re.compile(r"^approved://([a-z0-9][a-z0-9_-]{0,63})@([0-9a-f]{64})$")
SPLITS = {"train", "validation", "test"}
PREPROCESSING_VERSION = (
    "ffhq-user-image-v1+ffhq-wrinkle-texture-v1-bt709-dark-floor+yunet-max640-v2"
)


def sha256_file(path: Path) -> str:
    # Stream large files instead of loading entire checkpoints into memory.
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_path(uri: str, root: Path = APPROVED_DATA_ROOT) -> tuple[Path, str]:
    # Split the approved:// reference into a dataset directory and manifest hash.
    match = DATASET_URI.fullmatch(uri)
    if not match:
        raise ValueError("dataset_uri must be approved://<id>@<manifest_sha256>")
    manifest = root / match[1] / "manifest.json"
    # The resolved path must stay inside the approved root and match the hash.
    if (
        not manifest.resolve().is_relative_to(root.resolve())
        or not manifest.is_file()
        or sha256_file(manifest) != match[2]
    ):
        raise ValueError("approved dataset manifest is missing or changed")
    return manifest, match[2]


def _file(root: Path, name: str, digest: str) -> Path:
    # Reject absolute or traversal paths before opening a manifest-listed file.
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./-]*", name):
        raise ValueError("invalid dataset path")
    path = (root / name).resolve()
    # Verify both containment and the SHA-256 recorded in the manifest.
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("dataset file is missing or outside its directory")
    if not isinstance(digest, str) or sha256_file(path) != digest:
        raise ValueError("dataset file checksum mismatch")
    return path


def validate_manifest(path: Path) -> list[dict]:
    # Dataset metadata must document rights, training approval, and preprocessing.
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("dataset manifest must be an object")
    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("source") not in {"external_licensed", "consented_user_review"}
        or data.get("approved_for_training") is not True
        or not data.get("approval_reference")
        or not data.get("rights_reference")
        or data.get("preprocessing_version") != PREPROCESSING_VERSION
    ):
        raise ValueError("dataset approval, rights, or preprocessing contract is missing")
    if data["source"] == "consented_user_review":
        if (
            not data.get("consent_records")
            or not data.get("expires_at")
            or datetime.fromisoformat(data["expires_at"]) <= datetime.now(UTC)
        ):
            raise ValueError("user dataset consent or retention has expired")
    samples = data.get("samples")
    # A candidate requires at least one reviewed sample.
    if not isinstance(samples, list) or not samples:
        raise ValueError("dataset has no samples")
    seen, splits, subjects = set(), set(), {}
    checked = []
    for sample in samples:
        # Every entry belongs to exactly one supported split.
        if not isinstance(sample, dict) or sample.get("split") not in SPLITS:
            raise ValueError("invalid dataset split")
        sample_id = sample.get("id")
        if not isinstance(sample_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", sample_id):
            raise ValueError("invalid sample id")
        if sample_id in seen:
            raise ValueError("sample appears in multiple splits")
        # Keep all images from one person in one split to avoid identity leakage.
        subject_id = sample.get("subject_id")
        if not isinstance(subject_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", subject_id):
            raise ValueError("invalid subject id")
        if subject_id in subjects and subjects[subject_id] != sample["split"]:
            raise ValueError("subject appears in multiple splits")
        subjects[subject_id] = sample["split"]
        seen.add(sample_id)
        splits.add(sample["split"])
        checked.append(
            {
                "id": sample_id,
                "split": sample["split"],
                "input": _file(path.parent, sample.get("input"), sample.get("input_sha256")),
                "mask": _file(path.parent, sample.get("mask"), sample.get("mask_sha256")),
            }
        )
        # Inputs and labels must use the expected formats and bounded file sizes.
        if checked[-1]["input"].suffix != ".npy" or checked[-1]["mask"].suffix != ".png":
            raise ValueError("dataset requires .npy model inputs and .png masks")
        if checked[-1]["input"].stat().st_size > 20 * 1024 * 1024:
            raise ValueError("model input exceeds 20 MiB")
        if checked[-1]["mask"].stat().st_size > 4 * 1024 * 1024:
            raise ValueError("mask exceeds 4 MiB")
    if splits != SPLITS:
        # Evaluation requires held-out validation and test samples.
        raise ValueError("train, validation, and test splits are all required")
    return checked


def train_candidate(
    uri: str,
    epochs: int = 1,
    root: Path = APPROVED_DATA_ROOT,
    *,
    base_manifest: str | None = None,
    progress=None,
    check_consent=None,
    cancelled=None,
) -> dict:
    """Log a candidate and held-out metrics to the active MLflow run; never deploy it."""
    # Resolve and verify the external dataset before creating a model or checkpoint.
    if not 1 <= epochs <= 20:
        raise ValueError("epochs must be between 1 and 20")
    manifest, manifest_sha = dataset_path(uri, root)
    # Check manifest rules and each referenced file hash before importing PyTorch.
    samples = validate_manifest(manifest)

    import mlflow
    import numpy as np
    import torch
    from PIL import Image

    from ai.ffhq_wrinkle.modeling import load_wrinkle_model
    from backend.wrinkle.approved_model import approved_checkpoint

    def load(sample: dict) -> tuple[torch.Tensor, torch.Tensor]:
        # Refuse pickle while reading the four-channel model input.
        array = np.load(sample["input"], allow_pickle=False)
        with Image.open(sample["mask"]) as opened:
            if not 128 <= min(opened.size) <= max(opened.size) <= 1024:
                raise ValueError(f"invalid mask dimensions for sample {sample['id']}")
            mask = np.asarray(opened.convert("L"))
        # Validate paired dimensions, numeric range, and binary mask labels.
        if (
            array.dtype != np.float32
            or array.ndim != 3
            or array.shape[0] != 4
            or array.shape[1:] != mask.shape
            or min(mask.shape) < 128
            or max(mask.shape) > 1024
            or any(size % 16 for size in mask.shape)
            or not np.isfinite(array).all()
            or array.min() < -1
            or array.max() > 1
            or not np.isin(mask, [0, 255]).all()
        ):
            raise ValueError(f"invalid model input or mask for sample {sample['id']}")
        return torch.from_numpy(array.copy()).unsqueeze(0), torch.from_numpy(
            (mask > 0).astype(np.int64)
        ).unsqueeze(0)

    # Validate the entire dataset before creating a model or logging a candidate.
    for sample in samples:
        load(sample)
    torch.manual_seed(2024)
    bundle = load_wrinkle_model(
        "UNet",
        checkpoint_path=approved_checkpoint(base_manifest) if base_manifest else None,
        verify_official=not bool(base_manifest),
    )
    model = bundle.model
    device = bundle.device
    mlflow.log_params(
        {
            "base_checkpoint_sha256": bundle.checkpoint_sha256,
            "device": str(device),
            "training_kind": "fine_tuning",
        }
    )

    def evaluate() -> dict:
        model.eval()
        result = {}
        with torch.inference_mode():
            for split in ("validation", "test"):
                tp = fp = fn = 0
                positive_samples = 0
                sample_dice = []
                for sample in samples:
                    if sample["split"] != split:
                        continue
                    image, mask = load(sample)
                    truth = mask.to(device).bool()
                    positive_samples += int(truth.any())
                    prediction = model(image.to(device)).argmax(dim=1).bool()
                    a = int((prediction & truth).sum())
                    b = int((prediction & ~truth).sum())
                    c = int((~prediction & truth).sum())
                    tp += a
                    fp += b
                    fn += c
                    sample_dice.append(2 * a / (2 * a + b + c) if 2 * a + b + c else 1.0)
                result[f"{split}_dice"] = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0
                result[f"{split}_iou"] = tp / (tp + fp + fn) if tp + fp + fn else 1.0
                result[f"{split}_precision"] = tp / max(1, tp + fp)
                result[f"{split}_recall"] = tp / max(1, tp + fn)
                result[f"{split}_mean_dice"] = sum(sample_dice) / len(sample_dice)
                result[f"{split}_positive_samples"] = positive_samples
        return result

    baseline = evaluate()
    mlflow.log_metrics({f"base_{key}": value for key, value in baseline.items()})
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    for epoch in range(epochs):
        if check_consent:
            check_consent()
        model.train()
        losses = []
        for sample in samples:
            if cancelled and cancelled():
                raise RuntimeError("Training job was cancelled")
            # Only training-split samples update model weights.
            if sample["split"] != "train":
                continue
            image, mask = load(sample)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(model(image.to(device)), mask.to(device))
            # Backpropagate pixel-level classification loss through the U-Net.
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))
        mlflow.log_metric("train_loss", sum(losses) / len(losses), step=epoch)
        if progress:
            progress(epoch + 1, sum(losses) / len(losses))

    # Evaluate held-out splits without gradients or optimizer updates.
    metrics = evaluate()
    if check_consent:
        check_consent()
    # Log reproducibility fields and held-out metrics to the active MLflow run.
    mlflow.log_params({"architecture": "UNet", "epochs": epochs, "manifest_sha256": manifest_sha})
    mlflow.log_metrics(metrics)
    mlflow.set_tags(
        {
            "candidate_status": "awaiting_approval",
            "dataset_source": json.loads(manifest.read_text(encoding="utf-8"))["source"],
        }
    )
    with tempfile.TemporaryDirectory(prefix="aphrodize-candidate-") as directory:
        # Upload a candidate checkpoint; temporary local bytes disappear afterward.
        checkpoint = Path(directory) / "candidate_unet.pth"
        torch.save(model.state_dict(), checkpoint)
        mlflow.set_tag("checkpoint_sha256", sha256_file(checkpoint))
        mlflow.log_artifact(str(checkpoint), artifact_path="model")
        mlflow.log_dict({"candidate": metrics, "baseline": baseline}, "evaluation.json")
    return {
        "candidate": metrics,
        "baseline": baseline,
        "base_checkpoint_sha256": bundle.checkpoint_sha256,
    }
