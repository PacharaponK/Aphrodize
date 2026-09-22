import unittest

import numpy as np

from ai.ffhq_wrinkle.evaluation import fixed_bin
from ai.ffhq_wrinkle.metrics import (
    BinaryConfusion,
    binary_confusion,
    metrics_from_confusion,
    summarize_rows,
)


class BinaryMetricTests(unittest.TestCase):
    def test_known_confusion_and_metrics(self):
        prediction = np.array([[1, 1], [0, 0]], dtype=bool)
        target = np.array([[1, 0], [1, 0]], dtype=bool)
        confusion = binary_confusion(prediction, target)
        self.assertEqual(confusion, BinaryConfusion(1, 1, 1, 1))
        metrics = metrics_from_confusion(confusion)
        self.assertEqual(metrics["dice"], 0.5)
        self.assertEqual(metrics["iou"], 1 / 3)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["false_positive_area"], 0.25)

    def test_perfect_empty_masks_score_one(self):
        confusion = binary_confusion(
            np.zeros((3, 3), dtype=bool), np.zeros((3, 3), dtype=bool)
        )
        metrics = metrics_from_confusion(confusion)
        for key in ("dice", "iou", "precision", "recall"):
            self.assertEqual(metrics[key], 1.0)

    def test_empty_prediction_with_positive_target(self):
        confusion = BinaryConfusion(0, 0, 2, 2)
        metrics = metrics_from_confusion(confusion)
        self.assertEqual(metrics["precision"], 0.0)
        self.assertEqual(metrics["recall"], 0.0)
        self.assertEqual(metrics["dice"], 0.0)

    def test_shape_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            binary_confusion(np.zeros((2, 2)), np.zeros((2, 3)))

    def test_micro_and_macro_summaries_are_distinct(self):
        rows = [
            metrics_from_confusion(BinaryConfusion(1, 0, 0, 9)),
            metrics_from_confusion(BinaryConfusion(0, 9, 1, 0)),
        ]
        summary = summarize_rows(rows)
        self.assertEqual(summary["image_count"], 2)
        self.assertAlmostEqual(summary["micro"]["dice"], 1 / 6)
        self.assertEqual(summary["macro"]["dice"], 0.5)


class StratificationTests(unittest.TestCase):
    def test_fixed_bins_include_lower_and_exclude_upper_boundary(self):
        bins = {"low": (None, 10.0), "middle": (10.0, 20.0), "high": (20.0, None)}
        self.assertEqual(fixed_bin(9.99, bins), "low")
        self.assertEqual(fixed_bin(10.0, bins), "middle")
        self.assertEqual(fixed_bin(20.0, bins), "high")


if __name__ == "__main__":
    unittest.main()
