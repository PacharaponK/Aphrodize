import os
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

from ai.ffhq_wrinkle.alignment import YuNetFaceDetector
from ai.ffhq_wrinkle.paths import MODEL_ROOT


class DetectorRegressionTests(unittest.TestCase):
    def test_default_resize_preserves_original_coordinates(self):
        with patch("ai.ffhq_wrinkle.alignment.cv2.FaceDetectorYN.create") as create:
            create.return_value.detect.return_value = (
                None,
                np.array([[64, 128, 192, 256, *([100, 200] * 5), 0.9]], dtype=np.float32),
            )
            detector = YuNetFaceDetector(MODEL_ROOT / "face_detection_yunet_2023mar.onnx")
            face = detector.detect(np.zeros((1280, 960, 3), dtype=np.uint8))[0]
            create.return_value.setInputSize.assert_called_with((480, 640))
            self.assertEqual(face.bbox, (128, 256, 384, 512))
            np.testing.assert_array_equal(face.landmarks[0], [200, 400])

    @unittest.skipUnless(os.environ.get("APHRODIZE_TEST_IMAGE_DIR"), "private photos are opt-in")
    def test_seven_private_photos_two_faces_and_blank(self):
        root = Path(os.environ["APHRODIZE_TEST_IMAGE_DIR"])
        detector = YuNetFaceDetector(MODEL_ROOT / "face_detection_yunet_2023mar.onnx")
        images = []
        for index in range(1, 8):
            with Image.open(root / f"{index}.jpg") as opened:
                image = np.asarray(opened.convert("RGB"))
            images.append(image)
            self.assertEqual(len(detector.detect(image)), 1, f"photo {index}")
        self.assertEqual(len(detector.detect(np.concatenate([images[0], images[-1]], axis=1))), 2)
        self.assertEqual(len(detector.detect(np.zeros((800, 800, 3), dtype=np.uint8))), 0)


if __name__ == "__main__":
    unittest.main()
