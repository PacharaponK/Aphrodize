import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
from PIL import Image

from ai.ffhq_wrinkle.modeling import (
    CheckpointArchitectureError,
    ModelBundle,
    load_checkpoint_strict,
    resolve_device,
)
from ai.ffhq_wrinkle.prediction import (
    ThresholdConfig,
    create_overlay,
    ensure_output_available,
    infer_logits_and_probability,
    predict_image,
    threshold_probability,
)
from ai.ffhq_wrinkle.preprocess import PreprocessResult
from ai.ffhq_wrinkle.paths import DATA_ROOT, MODEL_ROOT


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class FixedSegmentationModel(torch.nn.Module):
    def forward(self, value):
        background = torch.zeros_like(value[:, :1])
        wrinkle = value[:, 3:4]
        return torch.cat((background, wrinkle), dim=1)


def fake_preprocessor(_image_path, output_dir, **_kwargs):
    size = 16
    aligned = np.full((size, size, 3), 100, dtype=np.uint8)
    face_mask = np.zeros((size, size), dtype=bool)
    face_mask[2:14, 2:14] = True
    masked = aligned.copy()
    masked[~face_mask] = 0
    texture = np.zeros((size, size), dtype=np.uint8)
    tensor = np.zeros((4, size, size), dtype=np.float32)
    tensor[3, 4:12, 4:12] = 1.0
    metadata = {
        "input_size": [size, size],
        "aligned_size": [size, size],
        "quality_flags": [],
        "quality_metrics": {"face_mask_ratio": float(face_mask.mean())},
        "artifacts": {},
    }
    return PreprocessResult(tensor, aligned, face_mask, masked, texture, metadata)


def fake_bundle(checkpoint: Path) -> ModelBundle:
    return ModelBundle(
        model=FixedSegmentationModel().eval(),
        architecture="UNet",
        checkpoint=checkpoint,
        checkpoint_sha256="a" * 64,
        device=torch.device("cpu"),
        device_metadata={
            "requested": "cpu",
            "selected": "cpu",
            "fallback_used": False,
        },
        load_seconds=0.01,
    )


class ModelOutputTests(unittest.TestCase):
    def test_inference_returns_logits_and_softmax_probability(self):
        tensor = np.zeros((4, 4, 4), dtype=np.float32)
        tensor[3] = 1.0
        logits, probability, elapsed = infer_logits_and_probability(
            FixedSegmentationModel(), tensor, torch.device("cpu")
        )
        self.assertEqual(logits.shape, (2, 4, 4))
        self.assertEqual(probability.shape, (4, 4))
        np.testing.assert_allclose(probability, 1.0 / (1.0 + np.exp(-1.0)))
        self.assertGreaterEqual(elapsed, 0.0)

    def test_threshold_is_versioned_and_limited_to_face(self):
        probability = np.array([[0.9, 0.9], [0.4, 0.6]], dtype=np.float32)
        face_mask = np.array([[True, False], [True, True]])
        config = ThresholdConfig(probability=0.5)
        result = threshold_probability(probability, face_mask, config)
        np.testing.assert_array_equal(result, [[True, False], [False, True]])
        self.assertTrue(config.version)

    def test_overlay_changes_only_selected_pixels(self):
        image = np.full((2, 2, 3), 100, dtype=np.uint8)
        mask = np.array([[True, False], [False, False]])
        overlay = create_overlay(image, mask, alpha=0.5)
        np.testing.assert_array_equal(overlay[1, 1], image[1, 1])
        self.assertGreater(int(overlay[0, 0, 0]), 100)


class DeviceAndCheckpointTests(unittest.TestCase):
    def test_explicit_cuda_falls_back_to_cpu_when_unavailable(self):
        with patch("torch.cuda.is_available", return_value=False):
            selected = resolve_device("cuda")
        self.assertEqual(selected.device.type, "cpu")
        self.assertTrue(selected.fallback_used)
        self.assertIsNotNone(selected.fallback_reason)

    def test_module_prefix_checkpoint_loads_strictly(self):
        source = torch.nn.Conv2d(1, 2, 1)
        target = torch.nn.Conv2d(1, 2, 1)
        checkpoint = {
            "model": {f"module.{key}": value for key, value in source.state_dict().items()}
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pth"
            torch.save(checkpoint, path)
            load_checkpoint_strict(target, path, torch.device("cpu"), "UNet")
        for expected, actual in zip(source.parameters(), target.parameters()):
            self.assertTrue(torch.equal(expected, actual))

    def test_architecture_mismatch_is_rejected(self):
        source = torch.nn.Conv2d(1, 2, 1)
        target = torch.nn.Linear(2, 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pth"
            torch.save(source.state_dict(), path)
            with self.assertRaises(CheckpointArchitectureError):
                load_checkpoint_strict(target, path, torch.device("cpu"), "UNet")


class OutputSafetyTests(unittest.TestCase):
    def test_nonempty_output_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result"
            output.mkdir()
            (output / "existing.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                ensure_output_available(output)
            self.assertEqual((output / "existing.txt").read_text(encoding="utf-8"), "keep")

    def test_prediction_saves_raw_and_visual_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result"
            result = predict_image(
                "unused.png",
                output,
                architecture="UNet",
                model_bundle=fake_bundle(Path(temp_dir) / "fake.pth"),
                preprocessor=fake_preprocessor,
            )
            self.assertEqual(result.logits.shape, (2, 16, 16))
            self.assertEqual(result.probability.shape, (16, 16))
            self.assertEqual(result.mask.shape, (16, 16))
            for filename in (
                "wrinkle_logits.npy",
                "wrinkle_probability.npy",
                "wrinkle_probability.png",
                "wrinkle_mask.png",
                "overlay.png",
                "result.json",
            ):
                self.assertTrue((output / filename).is_file(), filename)
            self.assertEqual(result.metadata["threshold"]["probability"], 0.5)


class OfficialArtifactIntegrationTests(unittest.TestCase):
    def test_official_unet_end_to_end(self):
        image = DATA_ROOT / "images1024x1024" / "00000" / "00001.png"
        checkpoint = (
            MODEL_ROOT
            / "stage2_wrinkle_finetune_unet"
            / "stage2_unet.pth"
        )
        yunet = MODEL_ROOT / "face_detection_yunet_2023mar.onnx"
        bisenet = MODEL_ROOT / "79999_iter.pth"
        if not all(path.is_file() for path in (image, checkpoint, yunet, bisenet)):
            self.skipTest("gitignored official inference artifacts are not available")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = predict_image(image, temp_dir, "UNet", checkpoint, "cpu")
            self.assertEqual(result.logits.shape, (2, 1024, 1024))
            self.assertEqual(result.probability.shape, (1024, 1024))
            self.assertEqual(result.mask.shape, (1024, 1024))
            self.assertGreater(int(result.mask.sum()), 0)
            with Image.open(Path(temp_dir) / "face_mask.png") as saved_mask:
                face_mask = np.asarray(saved_mask).copy() > 0
            self.assertEqual(np.count_nonzero(result.mask[~face_mask]), 0)
            self.assertEqual(result.metadata["model"]["architecture"], "UNet")


if __name__ == "__main__":
    unittest.main()
