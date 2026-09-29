import unittest

import numpy as np

from scripts.evaluate_uv_model import block_bootstrap_ci, threshold_counts


class EvaluationTest(unittest.TestCase):
    def test_paired_gain_and_undercall_counts(self):
        self.assertEqual(block_bootstrap_ci(np.ones(28), block=7), [1.0, 1.0])
        self.assertEqual(
            threshold_counts(np.array([10.4, 10.6, 11.8]), np.array([10.6, 10.4, 11.4]), 11),
            {"actual_at_or_above": 2, "undercalled": 1, "false_alarms": 1},
        )
