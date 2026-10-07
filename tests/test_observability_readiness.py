import io
import runpy
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/check-observability-readiness.py")
)
CHECK = MODULE["check_metrics"]


class ObservabilityReadinessTests(unittest.TestCase):
    def test_requires_a_successful_recent_collector(self):
        CHECK(
            f"aphrodize_collector_success 1.0\n"
            f"aphrodize_collector_timestamp_seconds {time.time()}\n"
        )
        for metrics in (
            "",
            f"aphrodize_collector_success 0.0\n"
            f"aphrodize_collector_timestamp_seconds {time.time()}\n",
            "aphrodize_collector_success 1.0\naphrodize_collector_timestamp_seconds 0.0\n",
        ):
            with self.subTest(metrics=metrics), self.assertRaises((AssertionError, KeyError)):
                CHECK(metrics)

    def test_retries_in_progress_collection_and_bounds_permanent_failure(self):
        check = MODULE["check"]
        settings = SimpleNamespace(
            observability_enabled=True, api_username="test", api_password="test"
        )
        healthy = (
            f"aphrodize_collector_success 1.0\n"
            f"aphrodize_collector_timestamp_seconds {time.time()}\n"
        ).encode()
        request = Mock(side_effect=[ConnectionError("temporary"), io.BytesIO(healthy)])
        with patch.dict(check.__globals__, urlopen=request, settings=settings), patch("time.sleep"):
            check()
        self.assertEqual(request.call_count, 2)
        request = Mock(side_effect=lambda *_args, **_kwargs: io.BytesIO(b""))
        with patch.dict(check.__globals__, urlopen=request, settings=settings), patch("time.sleep"):
            with self.assertRaises(KeyError):
                check()
        self.assertEqual(request.call_count, 6)


if __name__ == "__main__":
    unittest.main()
