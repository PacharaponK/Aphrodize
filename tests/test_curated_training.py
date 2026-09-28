"""The trainer must reject changed, unapproved, or identity-leaking datasets."""

import json
from pathlib import Path

import pytest

from backend.services.curated_training import (
    PREPROCESSING_VERSION,
    dataset_path,
    sha256_file,
    validate_manifest,
)
from backend.wrinkle import approved_model


def write_dataset(root: Path) -> tuple[Path, str]:
    directory = root / "pilot"
    directory.mkdir()
    samples = []
    for split in ("train", "validation", "test"):
        image = directory / f"{split}.npy"
        mask = directory / f"{split}.png"
        image.write_bytes(b"input")
        mask.write_bytes(b"mask")
        samples.append({
            "id": split,
            "subject_id": split,
            "split": split,
            "input": image.name,
            "input_sha256": sha256_file(image),
            "mask": mask.name,
            "mask_sha256": sha256_file(mask),
        })
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "source": "external_licensed",
        "approved_for_training": True,
        "approval_reference": "review-1",
        "rights_reference": "license-review-1",
        "preprocessing_version": PREPROCESSING_VERSION,
        "samples": samples,
    }), encoding="utf-8")
    return manifest, f"approved://pilot@{sha256_file(manifest)}"


def test_approved_dataset_is_pinned_and_split_by_subject(tmp_path: Path) -> None:
    manifest, uri = write_dataset(tmp_path)
    assert dataset_path(uri, tmp_path)[0] == manifest
    assert len(validate_manifest(manifest)) == 3

    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["samples"][1]["subject_id"] = data["samples"][0]["subject_id"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest is missing or changed"):
        dataset_path(uri, tmp_path)
    with pytest.raises(ValueError, match="multiple splits"):
        validate_manifest(manifest)


def test_user_data_is_not_an_approved_training_source(tmp_path: Path) -> None:
    manifest, _ = write_dataset(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["source"] = "label_studio_user_upload"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="approval"):
        validate_manifest(manifest)


def test_only_approved_unchanged_checkpoint_can_be_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(approved_model, "MODEL_ROOT", tmp_path)
    directory = tmp_path / "candidate"
    directory.mkdir()
    checkpoint = directory / "candidate_unet.pth"
    checkpoint.write_bytes(b"model")
    manifest = directory / "approved.json"
    manifest.write_text(json.dumps({
        "status": "approved",
        "architecture": "UNet",
        "preprocessing_version": PREPROCESSING_VERSION,
        "approval_reference": "review-1",
        "rights_reference": "license-review-1",
        "checkpoint": checkpoint.name,
        "checkpoint_sha256": sha256_file(checkpoint),
    }), encoding="utf-8")
    assert approved_model.approved_checkpoint(manifest) == checkpoint
    checkpoint.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        approved_model.approved_checkpoint(manifest)
