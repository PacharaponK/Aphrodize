import unittest

from ai.ffhq_wrinkle.area_assessment import assess_visible_area, evaluate_reviews


class AreaAssessmentTests(unittest.TestCase):
    def test_existing_score_cap_does_not_erase_audit_area_difference(self):
        import numpy as np

        from ai.ffhq_wrinkle.scoring import derive_scores

        face = np.ones((100, 100), dtype=bool)
        values = []
        for count in (500, 1000):
            mask = np.zeros_like(face)
            mask.flat[:count] = True
            values.append(derive_scores(mask, face, gate_passed=True)["overall"])
        self.assertEqual([value["score"] for value in values], [100, 100])
        audits = [assess_visible_area(v["wrinkle_pixels"], v["evaluated_pixels"]) for v in values]
        self.assertEqual([a["wrinkle_area_ratio"] for a in audits], [0.05, 0.1])

    def test_boundaries_preserve_uncapped_ratio_and_missing_measurement(self):
        for pixels, band in (
            (0, "none"),
            (164, "low"),
            (165, "medium"),
            (334, "medium"),
            (335, "high"),
            (10000, "high"),
        ):
            self.assertEqual(assess_visible_area(pixels, 10000)["visible_area_band"], band)
        low = assess_visible_area(500, 10000)
        high = assess_visible_area(1000, 10000)
        self.assertLess(low["wrinkle_area_ratio"], high["wrinkle_area_ratio"])
        self.assertFalse(high["recommendation_ready"])
        empty = assess_visible_area(0, 0)
        self.assertEqual(empty["visible_area_band"], "unavailable")
        self.assertIsNone(empty["wrinkle_area_ratio"])
        self.assertEqual(assess_visible_area(50, 1000), low)

    def test_invalid_counts_and_thresholds_are_rejected(self):
        for counts in ((True, 10), (1.0, 10), (-1, 10), (11, 10), (0, -1)):
            with self.assertRaises(ValueError):
                assess_visible_area(*counts)
        for boundary in (float("nan"), float("inf"), 0, -1, True, 0.04):
            with self.assertRaises(ValueError):
                assess_visible_area(1, 10, low_ratio=boundary)

    def test_review_agreement_excludes_unreadable_without_claiming_release(self):
        rows = [
            {
                "sample_id": str(i),
                "region": "overall",
                "reviewer_id": "r1",
                "predicted_band": "low",
                "human_band": human,
            }
            for i, human in enumerate(("low", "high", "unreadable", ""))
        ]
        result = evaluate_reviews(rows)
        self.assertEqual(result["comparable_rows"], 2)
        self.assertEqual(result["excluded_rows"], 1)
        self.assertEqual(result["exact_agreement"], 0.5)
        self.assertFalse(result["recommendation_ready"])
        self.assertIsNone(evaluate_reviews([])["exact_agreement"])
        with self.assertRaises(ValueError):
            evaluate_reviews([rows[0], rows[0]])
        with self.assertRaises(ValueError):
            evaluate_reviews([{**rows[0], "reviewer_id": ""}])

    def test_independent_raters_and_repeat_captures(self):
        first = {
            "sample_id": "a",
            "subject_id": "p1",
            "repeat_id": "1",
            "region": "overall",
            "reviewer_id": "r1",
            "human_band": "low",
            "predicted_band": "low",
            "area_ratio": "0.01",
        }
        second = {**first, "reviewer_id": "r2", "human_band": "medium"}
        repeat = {
            **first,
            "sample_id": "b",
            "repeat_id": "2",
            "predicted_band": "medium",
            "area_ratio": "0.02",
        }
        result = evaluate_reviews([first, second, repeat])
        self.assertEqual(result["multi_rater_regions"], 1)
        self.assertEqual(result["unanimous_rater_agreement"], 0)
        self.assertEqual(result["repeatability"][0]["sample_count"], 2)
        self.assertAlmostEqual(result["repeatability"][0]["area_range_percentage_points"], 1)
        self.assertFalse(result["repeatability"][0]["same_band"])

        unlabelled = evaluate_reviews([{**first, "human_band": ""}, {**repeat, "human_band": ""}])
        self.assertEqual(unlabelled["reviewed_rows"], 0)
        self.assertIsNone(unlabelled["exact_agreement"])
        self.assertEqual(unlabelled["repeatability"][0]["sample_count"], 2)
        with self.assertRaises(ValueError):
            evaluate_reviews([first, {**second, "area_ratio": "0.05"}])


if __name__ == "__main__":
    unittest.main()
