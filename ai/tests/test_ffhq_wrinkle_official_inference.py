import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from ai.ffhq_wrinkle.prepare_phase1_data import image_location, read_image_ids


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_ROOT = REPOSITORY_ROOT / "ai" / "ffhq_wrinkle" / "official"


def load_official_inference_module():
    sys.path.insert(0, str(OFFICIAL_ROOT))
    try:
        spec = importlib.util.spec_from_file_location(
            "ffhq_wrinkle_official_inference", OFFICIAL_ROOT / "inference.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(OFFICIAL_ROOT))


class OfficialInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.official = load_official_inference_module()

    def test_rgb_then_texture_channel_order_and_normalization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "sample.png"
            texture_path = root / "texture.png"
            rgb = np.array([[[0, 127, 255], [255, 0, 127]]], dtype=np.uint8)
            texture = np.array([[255, 0]], dtype=np.uint8)
            Image.fromarray(rgb, mode="RGB").save(image_path)
            Image.fromarray(texture, mode="L").save(texture_path)

            dataset = self.official.WrinkleTestDataset(image_path, texture_path)
            tensor, filename = dataset[0]

            self.assertEqual(filename, "sample.png")
            self.assertEqual(tuple(tensor.shape), (4, 1, 2))
            np.testing.assert_allclose(tensor[0].numpy(), [[-1.0, 1.0]])
            np.testing.assert_allclose(
                tensor[1].numpy(), [[127.0 / 255.0 * 2.0 - 1.0, -1.0]], rtol=0, atol=1e-7
            )
            np.testing.assert_allclose(
                tensor[2].numpy(), [[1.0, 127.0 / 255.0 * 2.0 - 1.0]], rtol=0, atol=1e-7
            )
            np.testing.assert_allclose(tensor[3].numpy(), [[1.0, -1.0]])

    def test_module_prefix_is_removed_during_checkpoint_loading(self):
        source = torch.nn.Linear(2, 1)
        target = torch.nn.Linear(2, 1)
        prefixed = {f"module.{key}": value for key, value in source.state_dict().items()}
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "checkpoint.pth"
            torch.save({"model": prefixed}, checkpoint_path)
            self.official.load_checkpoint(target, checkpoint_path, torch.device("cpu"))
        for expected, actual in zip(source.parameters(), target.parameters()):
            self.assertTrue(torch.equal(expected, actual))


class Phase1DataPreparationTests(unittest.TestCase):
    def test_image_location_matches_ffhq_grouping_and_mirror_parts(self):
        url, destination = image_location("09269", Path("dataset"))
        self.assertTrue(url.endswith("/Part1/09269.png"))
        self.assertEqual(destination, Path("dataset/images1024x1024/09000/09269.png"))

        url, destination = image_location("10280", Path("dataset"))
        self.assertTrue(url.endswith("/Part2/10280.png"))
        self.assertEqual(destination, Path("dataset/images1024x1024/10000/10280.png"))

    def test_read_image_ids_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ids.txt"
            path.write_text("00001\n00001\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_image_ids(path)


if __name__ == "__main__":
    unittest.main()
