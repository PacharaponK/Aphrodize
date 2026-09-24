import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from ai.ffhq_wrinkle.face_parsing import (
    DEFAULT_FACE_LABELS,
    face_mask_from_labels,
    load_bisenet,
    parse_face,
    resize_label_map,
)
from ai.ffhq_wrinkle.texture_map import (
    GAUSSIAN_KERNEL_SIZE,
    GAUSSIAN_SIGMA,
    PREPROCESSING_VERSION,
    TextureMapConfig,
    generate_from_files,
    generate_texture_map,
)
from ai.ffhq_wrinkle.paths import DATA_ROOT, MODEL_ROOT


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class TextureFormulaTests(unittest.TestCase):
    def test_paper_parameters_and_selected_version_are_pinned(self):
        config = TextureMapConfig()
        self.assertEqual(GAUSSIAN_KERNEL_SIZE, 21)
        self.assertEqual(GAUSSIAN_SIGMA, 5.0)
        self.assertEqual(config.kernel_size, 21)
        self.assertEqual(config.sigma, 5.0)
        self.assertEqual(config.intensity_method, "bt709_float")
        self.assertEqual(config.response_mode, "dark_only_floor")
        self.assertIn("bt709-dark-floor", PREPROCESSING_VERSION)

    def test_constant_image_matches_paper_equation(self):
        image = np.full((32, 32, 3), 100, dtype=np.uint8)
        texture = generate_texture_map(image)
        expected = round((1.0 - 100.0 / 101.0) * 255.0)
        self.assertEqual(texture.dtype, np.uint8)
        self.assertEqual(texture.shape, (32, 32))
        np.testing.assert_array_equal(texture, expected)

    def test_texture_is_continuous_grayscale_not_binary_otsu(self):
        ramp = np.tile(np.arange(64, dtype=np.uint8), (64, 1)) * 4
        image = np.repeat(ramp[:, :, None], 3, axis=2)
        texture = generate_texture_map(image)
        self.assertGreater(np.unique(texture).size, 2)

    def test_invalid_even_kernel_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "odd"):
            TextureMapConfig(kernel_size=20).validate()


class FaceMaskingTests(unittest.TestCase):
    def test_only_skin_and_nose_labels_are_kept(self):
        labels = np.array([[0, 1, 10, 17]], dtype=np.uint8)
        np.testing.assert_array_equal(
            face_mask_from_labels(labels), [[False, True, True, False]]
        )
        self.assertEqual(DEFAULT_FACE_LABELS, (1, 10))

    def test_label_resize_uses_nearest_neighbor(self):
        labels = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        expected = np.repeat(np.repeat(labels, 2, axis=0), 2, axis=1)
        np.testing.assert_array_equal(resize_label_map(labels, (4, 4)), expected)

    def test_non_face_pixels_are_zero_in_saved_1024_map(self):
        image = np.full((1024, 1024, 3), 100, dtype=np.uint8)
        labels = np.zeros((512, 512), dtype=np.uint8)
        labels[128:384, 128:384] = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "image.png"
            labels_path = root / "labels.npy"
            output_path = root / "texture.png"
            Image.fromarray(image, mode="RGB").save(image_path)
            np.save(labels_path, labels, allow_pickle=False)
            output = generate_from_files(image_path, labels_path, output_path)
            self.assertEqual(output.shape, (1024, 1024))
            self.assertEqual(output.dtype, np.uint8)
            self.assertEqual(int(output[0, 0]), 0)
            self.assertGreater(int(output[512, 512]), 0)
            with Image.open(output_path) as saved:
                self.assertEqual(saved.mode, "L")


class OfficialArtifactIntegrationTests(unittest.TestCase):
    def test_default_config_reproduces_official_weak_map_with_low_mae(self):
        image_path = DATA_ROOT / "images1024x1024" / "00000" / "00001.png"
        labels_path = DATA_ROOT / "face-parsed-labels" / "00001.npy"
        weak_path = DATA_ROOT / "weak_wrinkle_masks" / "00000" / "00001.png"
        if not all(path.is_file() for path in (image_path, labels_path, weak_path)):
            self.skipTest("gitignored official Phase 2 artifacts are not available")
        image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
        labels = np.load(labels_path, allow_pickle=False)
        mask = face_mask_from_labels(labels, image.shape[:2])
        predicted = generate_texture_map(image, mask)
        official = np.asarray(Image.open(weak_path).convert("L"), dtype=np.uint8)
        mae = np.abs(predicted.astype(np.int16) - official.astype(np.int16)).mean()
        self.assertLess(mae, 1.0)

    def test_bisenet_checkpoint_is_compatible_with_official_labels(self):
        checkpoint = MODEL_ROOT / "79999_iter.pth"
        image_path = DATA_ROOT / "images1024x1024" / "00000" / "00001.png"
        labels_path = DATA_ROOT / "face-parsed-labels" / "00001.npy"
        if not all(path.is_file() for path in (checkpoint, image_path, labels_path)):
            self.skipTest("gitignored BiSeNet validation artifacts are not available")
        image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
        predicted = parse_face(image, load_bisenet(checkpoint))
        official = np.load(labels_path, allow_pickle=False)
        self.assertGreater(float(np.mean(predicted == official)), 0.999)


if __name__ == "__main__":
    unittest.main()
