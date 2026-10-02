"""Check whether WOUDC has UV observations for the three Thai target areas."""

import json
from collections import Counter
from urllib.request import urlopen

URL = "https://api.woudc.org/collections/data_records/items?bbox=97,5,101,21&limit=1000&f=json"
UV_CATEGORIES = {"Broadband", "Multiband", "Spectral", "UVIndex"}


def main():
    with urlopen(URL, timeout=30) as response:
        data = json.load(response)
    if data["numberMatched"] != data["numberReturned"]:
        raise RuntimeError("WOUDC response was truncated; inspect pagination before deciding")
    counts = Counter(
        (item["properties"]["platform_name"], item["properties"]["content_category"])
        for item in data["features"]
    )
    print(f"WOUDC Thailand bbox records: {data['numberMatched']}")
    for (station, category), count in sorted(counts.items()):
        print(f"{station}: {category}: {count}")
    uv_count = sum(count for (_, category), count in counts.items() if category in UV_CATEGORIES)
    print(f"UV observation records: {uv_count}")


if __name__ == "__main__":
    main()
