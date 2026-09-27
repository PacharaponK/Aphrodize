import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(
    0,
    str(Path(__file__).parents[1] / "models" / "non-time-series" / "wrinkle-prototype"),
)
from wrinkle_prototype import PreprocessConfig, analyze, score_mask


class WrinklePrototypeTests(unittest.TestCase):
    def test_preprocess_and_score(self):
        mask = np.zeros((10, 10), dtype=bool)
        mask[:2, :] = True
        result = score_mask(mask, PreprocessConfig())
        self.assertEqual(result["wrinkle_area_ratio"], 0.2)
        self.assertEqual(result["wrinkle_score"], 100.0)
        self.assertEqual(result["severity"], "high")

    def test_load_and_resize_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path, mask_path = root / "face.png", root / "mask.png"
            Image.new("RGB", (40, 20), "gray").save(image_path)
            mask = np.zeros((20, 40), dtype=np.uint8)
            mask[:, :20] = 255
            Image.fromarray(mask).save(mask_path)
            result = analyze(image_path, mask_path, PreprocessConfig(image_size=16))
            self.assertEqual(result["image"]["preprocessed_shape"], [16, 16, 3])
            self.assertAlmostEqual(result["wrinkle_area_ratio"], 0.5)
