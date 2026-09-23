import random
import tempfile
import unittest
from pathlib import Path

from ai.ffhq_wrinkle.reproducibility import seed_everything
from ai.ffhq_wrinkle.paths import DATA_ROOT, MODEL_ROOT, REPOSITORY_ROOT
from ai.ffhq_wrinkle.verify_phase0 import parse_manifest


class ReproducibilityTests(unittest.TestCase):
    def test_python_random_is_repeatable(self):
        seed_everything(123)
        first = [random.random() for _ in range(4)]
        seed_everything(123)
        second = [random.random() for _ in range(4)]
        self.assertEqual(first, second)

    def test_negative_seed_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            seed_everything(-1)

    def test_large_artifacts_live_outside_source_tree(self):
        self.assertEqual(DATA_ROOT, REPOSITORY_ROOT / "storage" / "data" / "ffhq-wrinkle")
        self.assertEqual(MODEL_ROOT, REPOSITORY_ROOT / "storage" / "models" / "ffhq-wrinkle")
        self.assertFalse((REPOSITORY_ROOT / "ai" / "ffhq-wrinkle").exists())


class ManifestTests(unittest.TestCase):
    def test_manifest_parser(self):
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "checksums.sha256"
            manifest.write_text(f"# comment\n{digest}  42  model.pth\n", encoding="utf-8")
            self.assertEqual(parse_manifest(manifest), {"model.pth": (digest, 42)})

    def test_manifest_rejects_bad_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "checksums.sha256"
            manifest.write_text("not-a-hash  42  model.pth\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid SHA-256"):
                parse_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
