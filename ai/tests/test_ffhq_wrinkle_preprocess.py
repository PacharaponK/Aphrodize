import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from ai.ffhq_wrinkle.alignment import FaceDetection, align_face
from ai.ffhq_wrinkle.preprocess import (
    build_four_channel_tensor,
    load_user_image,
    preprocess_image,
)
from ai.ffhq_wrinkle.quality import QualityGateError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPOSITORY_ROOT / "ai" / "ffhq-wrinkle"


def valid_detection(width=320, height=320, confidence=0.99):
    return FaceDetection(
        (width * 0.25, height * 0.18, width * 0.50, height * 0.64),
        np.array(
            [
                [width * 0.375, height * 0.40],
                [width * 0.625, height * 0.40],
                [width * 0.500, height * 0.53],
                [width * 0.405, height * 0.66],
                [width * 0.595, height * 0.66],
            ],
            dtype=np.float32,
        ),
        confidence,
    )


def sharp_fixture(size=320):
    yy, xx = np.indices((size, size))
    checker = (((xx // 8 + yy // 8) % 2) * 90 + 80).astype(np.uint8)
    return np.stack((checker, np.roll(checker, 3, axis=1), checker), axis=2)


def valid_parser(_image):
    labels = np.zeros((512, 512), dtype=np.uint8)
    labels[96:416, 96:416] = 1
    labels[220:300, 230:282] = 10
    return labels


class FakeDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, _image):
        return list(self.detections)


class InputFormatTests(unittest.TestCase):
    def test_jpeg_png_and_webp_are_accepted(self):
        image = sharp_fixture()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for image_format, extension in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
                with self.subTest(image_format=image_format):
                    source = root / f"input.{extension}"
                    Image.fromarray(image, mode="RGB").save(source, format=image_format)
                    loaded, detected_format = load_user_image(source)
                    self.assertEqual(detected_format, image_format)
                    self.assertEqual(loaded.shape, image.shape)
                    result = preprocess_image(
                        source,
                        root / f"output-{extension}",
                        detector=FakeDetector([valid_detection()]),
                        parser=valid_parser,
                    )
                    self.assertEqual(result.tensor.shape, (4, 1024, 1024))
                    self.assertEqual(result.tensor.dtype, np.float32)
                    self.assertEqual(result.metadata["status"], "completed")


class AlignmentTests(unittest.TestCase):
    def test_alignment_is_deterministic(self):
        image = sharp_fixture()
        detection = valid_detection()
        first = align_face(image, detection)
        second = align_face(image, detection)
        self.assertEqual(first.shape, (1024, 1024, 3))
        np.testing.assert_array_equal(first, second)


class QualityGateTests(unittest.TestCase):
    def assert_rejected_before_parser(self, detections, expected_issue, image=None):
        calls = []

        def parser(value):
            calls.append(value)
            return valid_parser(value)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "input.png"
            Image.fromarray(image if image is not None else sharp_fixture(), mode="RGB").save(source)
            output = root / "output"
            output.mkdir()
            np.save(output / "model_input.npy", np.ones((1,), dtype=np.float32))
            with self.assertRaises(QualityGateError) as raised:
                preprocess_image(
                    source,
                    output,
                    detector=FakeDetector(detections),
                    parser=parser,
                )
            self.assertIn(expected_issue, raised.exception.assessment.issues)
            self.assertEqual(calls, [])
            self.assertFalse((output / "model_input.npy").exists())
            metadata = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertFalse(metadata["model_input_created"])

    def test_no_face_is_rejected(self):
        self.assert_rejected_before_parser([], "no_face_detected")

    def test_multiple_faces_are_rejected(self):
        self.assert_rejected_before_parser(
            [valid_detection(), valid_detection()], "multiple_faces_detected"
        )

    def test_low_resolution_is_rejected(self):
        image = sharp_fixture(128)
        self.assert_rejected_before_parser(
            [valid_detection(128, 128)], "resolution_too_low", image
        )

    def test_small_face_is_rejected(self):
        detection = valid_detection()
        too_small = FaceDetection((120, 120, 60, 60), detection.landmarks, 0.99)
        self.assert_rejected_before_parser([too_small], "face_too_small_pixels")

    def test_low_landmark_confidence_is_rejected(self):
        self.assert_rejected_before_parser(
            [valid_detection(confidence=0.4)], "landmark_confidence_too_low"
        )

    def test_dark_and_blurry_image_is_rejected(self):
        image = np.full((320, 320, 3), 5, dtype=np.uint8)
        self.assert_rejected_before_parser(
            [valid_detection()], "exposure_too_dark", image
        )

    def test_excessive_pose_is_rejected(self):
        detection = valid_detection()
        points = detection.landmarks.copy()
        points[1, 1] += 100
        tilted = FaceDetection(detection.bbox, points, detection.confidence)
        self.assert_rejected_before_parser([tilted], "pose_roll_excessive")

    def test_invalid_parsing_area_is_rejected_without_tensor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "input.png"
            output = root / "output"
            Image.fromarray(sharp_fixture(), mode="RGB").save(source)
            with self.assertRaises(QualityGateError) as raised:
                preprocess_image(
                    source,
                    output,
                    detector=FakeDetector([valid_detection()]),
                    parser=lambda _image: np.zeros((512, 512), dtype=np.uint8),
                )
            self.assertIn("face_parsing_area_too_small", raised.exception.assessment.issues)
            self.assertFalse((output / "model_input.npy").exists())


class TensorTests(unittest.TestCase):
    def test_rgb_texture_order_and_official_normalization(self):
        rgb = np.array([[[0, 127, 255]]], dtype=np.uint8)
        texture = np.array([[64]], dtype=np.uint8)
        tensor = build_four_channel_tensor(rgb, texture)
        self.assertEqual(tensor.shape, (4, 1, 1))
        np.testing.assert_allclose(
            tensor[:, 0, 0],
            np.array([0, 127, 255, 64], dtype=np.float32) / 255.0 * 2.0 - 1.0,
            rtol=0,
            atol=1e-7,
        )


class OfficialArtifactIntegrationTests(unittest.TestCase):
    def test_real_detector_parser_and_alignment_pipeline(self):
        image = DATA_ROOT / "images1024x1024" / "00000" / "00001.png"
        yunet = DATA_ROOT / "pretrained_ckpt" / "face_detection_yunet_2023mar.onnx"
        bisenet = DATA_ROOT / "pretrained_ckpt" / "79999_iter.pth"
        if not all(path.is_file() for path in (image, yunet, bisenet)):
            self.skipTest("gitignored Phase 3 integration artifacts are not available")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = preprocess_image(image, temp_dir, yunet, bisenet)
            self.assertEqual(result.tensor.shape, (4, 1024, 1024))
            self.assertEqual(result.aligned_face.shape, (1024, 1024, 3))
            self.assertEqual(result.face_mask.shape, (1024, 1024))
            self.assertEqual(np.count_nonzero(result.masked_face[~result.face_mask]), 0)
            self.assertTrue(result.metadata["model_input_created"])


if __name__ == "__main__":
    unittest.main()
