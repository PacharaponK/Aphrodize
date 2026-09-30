"""Download and validate TEMIS daily clear-sky UV data for three Thai cities."""

import csv
import hashlib
import math
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


SOURCES = {
    "bangkok": "uv_Bangkok_Thailand.dat",
    "songkhla": "uv_Songkhla_Thailand.dat",
    "chiang_mai": "uv_Chiang_Mai_Thailand.dat",
}
BASE_URL = "https://d1qb6yzwaaq4he.cloudfront.net/uvradiation/v2.0/overpass/"
OUTPUT = Path(__file__).resolve().parents[1] / "storage/data/uv/temis_clear_sky_uv.csv"


def parse_series(city: str, content: bytes) -> list[tuple[str, str, str, str]]:
    source = content.decode("utf-8")
    if "2, 3 = UVIEF, UVIEFerr" not in source:
        raise ValueError(f"{city}: TEMIS UVIEF column definition not found")
    rows = []
    previous = None
    for line_number, line in enumerate(source.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 17:
            raise ValueError(f"{city}:{line_number}: expected 17 columns, got {len(fields)}")
        if len(fields[0]) != 8 or not fields[0].isdigit():
            raise ValueError(f"{city}:{line_number}: invalid date {fields[0]}")
        day = date.fromisoformat(f"{fields[0][:4]}-{fields[0][4:6]}-{fields[0][6:8]}")
        if previous is not None and day != previous + timedelta(days=1):
            raise ValueError(f"{city}:{line_number}: date after {previous} is {day}")
        previous = day
        values = []
        for value in fields[1:3]:
            number = float(value)
            if not math.isfinite(number) or (number < 0 and number != -1):
                raise ValueError(f"{city}:{line_number}: invalid UV value {value}")
            values.append("" if number == -1 else value)
        rows.append((day.isoformat(), city, *values))
    if not rows:
        raise ValueError(f"{city}: no daily records")
    return rows


def main() -> None:
    all_rows = []
    for city, filename in SOURCES.items():
        request = Request(BASE_URL + filename, headers={"User-Agent": "Aphrodize-UV-Research/1.0"})
        with urlopen(request, timeout=60) as response:
            content = response.read()
        rows = parse_series(city, content)
        all_rows.extend(rows)
        missing = sum(not row[2] for row in rows)
        print(f"{city}: {len(rows)} dates, {rows[0][0]} to {rows[-1][0]}, "
              f"{missing} missing UV values, SHA-256 {hashlib.sha256(content).hexdigest()}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".csv.tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("date", "city", "uv_index_clear_sky", "uv_index_uncertainty"))
            writer.writerows(sorted(all_rows))
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Wrote {len(all_rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
