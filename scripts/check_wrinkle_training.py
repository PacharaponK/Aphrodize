"""Real U-Net fine-tuning check using temporary synthetic data, no services or user photos.

Run inside the trainer image: python /app/scripts/check_wrinkle_training.py
"""

import gc
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import mlflow
import numpy as np
import torch
from PIL import Image

from ai.ffhq_wrinkle.modeling import create_model
from backend.services.curated_training import PREPROCESSING_VERSION, sha256_file, train_candidate
from backend.wrinkle import approved_model


def main():
    torch.set_num_threads(2)
    torch.manual_seed(2024)
    with tempfile.TemporaryDirectory(prefix="wrinkle-self-check-") as temporary:
        root = Path(temporary)
        model = create_model("UNet")
        checkpoint = root / "base.pth"
        torch.save(model.state_dict(), checkpoint)
        del model
        gc.collect()
        digest = sha256_file(checkpoint)
        base_manifest = root / "approved.json"
        base_manifest.write_text(
            json.dumps(
                {
                    "status": "approved",
                    "architecture": "UNet",
                    "checkpoint": "base.pth",
                    "checkpoint_sha256": digest,
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "approval_reference": "synthetic-self-check",
                    "rights_reference": "synthetic",
                }
            )
        )
        directory = root / "dataset"
        directory.mkdir()
        samples = []
        for i, split in enumerate(("train", "validation", "test")):
            image = directory / f"{split}.npy"
            mask = directory / f"{split}.png"
            array = np.random.default_rng(i).uniform(-1, 1, (4, 128, 128)).astype(np.float32)
            np.save(image, array, allow_pickle=False)
            label = np.zeros((128, 128), dtype=np.uint8)
            label[40:70, 60:65] = 255
            Image.fromarray(label).save(mask)
            samples.append(
                {
                    "id": split,
                    "subject_id": split,
                    "split": split,
                    "input": image.name,
                    "mask": mask.name,
                    "input_sha256": sha256_file(image),
                    "mask_sha256": sha256_file(mask),
                }
            )
        manifest = directory / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source": "external_licensed",
                    "approved_for_training": True,
                    "approval_reference": "synthetic-self-check",
                    "rights_reference": "synthetic",
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "samples": samples,
                }
            )
        )
        recorded, progress, consent_checks = [], [], []

        def artifact(path, **_):
            recorded.append(sha256_file(Path(path)))

        with (
            patch.object(approved_model, "MODEL_ROOT", root),
            patch.object(mlflow, "log_params"),
            patch.object(mlflow, "log_metric"),
            patch.object(mlflow, "log_metrics"),
            patch.object(mlflow, "set_tags"),
            patch.object(mlflow, "set_tag"),
            patch.object(mlflow, "log_dict"),
            patch.object(mlflow, "log_artifact", artifact),
        ):
            result = train_candidate(
                f"approved://dataset@{sha256_file(manifest)}",
                root=root,
                base_manifest=str(base_manifest),
                progress=lambda epoch, loss: progress.append((epoch, loss)),
                check_consent=lambda: consent_checks.append(True),
            )
        assert result["base_checkpoint_sha256"] == digest
        assert len(recorded) == 1 and recorded[0] != digest, "Training must update existing weights"
        assert progress[0][0] == 1 and np.isfinite(progress[0][1])
        assert len(consent_checks) >= 2
        assert all(np.isfinite(value) for value in result["candidate"].values())
        assert set(result["candidate"]) == set(result["baseline"])
        print("PASS: real U-Net loaded, fine-tuned, evaluated and checkpointed; consent rechecked")


if __name__ == "__main__":
    main()
