"""Build static province paths/representative points from reviewed public data.

Usage: python scripts/prepare_uv_map.py boundaries.geojson provinces.json
See frontend/src/components/uv/DATA-LICENSE.md for pinned sources/licences.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_POINTS = {
    "bangkok": (13.7563, 100.5018),
    "songkhla": (7.1988, 100.5951),
    "chiang_mai": (18.7883, 98.9853),
}


def normalized(name):
    return re.sub(r"[^a-z]", "", name.lower().removesuffix(" Province".lower()))


def representative_point(ring):
    # ponytail: one interior point per province; sample more points for spatial averages.
    # Interior midpoint of the widest horizontal intersection of the main island.
    y = (min(p[1] for p in ring) + max(p[1] for p in ring)) / 2
    crossings = sorted(
        a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        for a, b in zip(ring, ring[1:], strict=False)
        if (a[1] > y) != (b[1] > y)
    )
    left, right = max(zip(crossings[::2], crossings[1::2], strict=False), key=lambda p: p[1] - p[0])
    return round(y, 5), round((left + right) / 2, 5)


def build(geometry, names):
    lookup = {normalized(p["name"]["en"]): p for p in names}
    records, shapes = [], []
    for feature in geometry["features"]:
        province = lookup[normalized(feature["properties"]["shapeName"])]
        name_en = province["name"]["en"]
        province_id = name_en.lower().replace(" ", "_")
        shape = feature["geometry"]
        polygons = (
            shape["coordinates"] if shape["type"] == "MultiPolygon" else [shape["coordinates"]]
        )
        main_ring = max(
            (p[0] for p in polygons),
            key=lambda ring: abs(
                sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:], strict=False))
            ),
        )
        latitude, longitude = MODEL_POINTS.get(province_id, representative_point(main_ring))
        paths = []
        for polygon in polygons:
            for ring in polygon:
                points = [f"{(lon - 97) * 80:.1f},{(21 - lat) * 80:.1f}" for lon, lat, *_ in ring]
                paths.append("M" + "L".join(points) + "Z")
        records.append(
            {
                "id": province_id,
                "name": province["name"]["th"],
                "name_en": name_en,
                "latitude": latitude,
                "longitude": longitude,
                "model_city": province_id if province_id in MODEL_POINTS else None,
            }
        )
        shapes.append({"id": province_id, "name": province["name"]["th"], "path": "".join(paths)})
    assert len(records) == len({p["id"] for p in records}) == 77
    assert sum(p["model_city"] is not None for p in records) == 3
    assert all(5 < p["latitude"] < 21 and 97 < p["longitude"] < 106 for p in records)
    return sorted(records, key=lambda p: p["id"]), sorted(shapes, key=lambda p: p["id"])


if __name__ == "__main__":
    records, shapes = build(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")),
        json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig")),
    )
    outputs = {
        ROOT / "backend/libs/uv_provinces.json": records,
        ROOT / "frontend/public/assets/uv-map-provinces.json": [
            {**record, "path": shape["path"]}
            for record, shape in zip(records, shapes, strict=True)
        ],
    }
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
    print("Prepared 77 province paths and representative points")
