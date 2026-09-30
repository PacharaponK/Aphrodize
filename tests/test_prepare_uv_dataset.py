import unittest

from scripts.prepare_uv_dataset import parse_series


class TemisParserTest(unittest.TestCase):
    def test_preserves_missing_dates_and_rejects_duplicates(self):
        def line(day, uv):
            return f"{day} {uv} 0.100 " + " ".join(["0.000"] * 14)

        header = "# 2, 3 = UVIEF, UVIEFerr : cloud-free erythemal UV index\n"
        content = (header + line("20260101", "10.000") + "\n" + line("20260102", "-1.000")).encode()
        rows = parse_series("bangkok", content)
        self.assertEqual([row[2] for row in rows], ["10.000", ""])

        duplicate = (header + line("20260101", "10.000") + "\n" + line("20260101", "11.000")).encode()
        with self.assertRaisesRegex(ValueError, "date after"):
            parse_series("bangkok", duplicate)
