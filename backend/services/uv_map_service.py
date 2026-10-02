"""Serve one selected UV source: the three local models or nationwide API forecasts."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from backend.services.uv_service import SNAPSHOT, load_recommendation, uv_level

PROVINCES = json.loads(
    (Path(__file__).resolve().parents[1] / "libs/uv_provinces.json").read_text(encoding="utf-8")
)
MAP_SNAPSHOT = SNAPSHOT.with_name("map_snapshot.json")


def valid_uv(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
        and 0 <= value <= 25
    )


def fresh(timestamp, now):
    try:
        generated = datetime.fromisoformat(timestamp)
        return generated.tzinfo is not None and -timedelta(
            minutes=5
        ) <= now - generated <= timedelta(hours=8)
    except (TypeError, ValueError):
        return False


def refresh_api_map(today, *, fetch=urlopen, now=None):
    """Refresh in batches; retain still-fresh prior records if one batch fails."""
    now = now or datetime.now(UTC)
    try:
        cached = json.loads(MAP_SNAPSHOT.read_text(encoding="utf-8"))["provinces"]
        if not isinstance(cached, dict):
            cached = {}
    except (OSError, ValueError, KeyError, TypeError):
        cached = {}
    provinces = PROVINCES
    # Only retain valid records from our known API provinces, including nulls for gaps.
    cached = {
        p["id"]: {
            "generated_at": record.get("generated_at"),
            "days": [
                {
                    "date": entry["date"],
                    "uv_index": entry["uv_index"] if valid_uv(entry.get("uv_index")) else None,
                }
                for entry in record.get("days", [])
                if isinstance(entry, dict) and isinstance(entry.get("date"), str)
            ],
        }
        for p in provinces
        if isinstance(record := cached.get(p["id"]), dict)
        and isinstance(record.get("generated_at"), str)
        and isinstance(record.get("days"), list)
    }
    dates = [today.isoformat(), (today + timedelta(days=1)).isoformat()]
    failures = 0
    for start in range(0, len(provinces), 20):
        batch = provinces[start : start + 20]
        query = urlencode(
            {
                "latitude": ",".join(str(p["latitude"]) for p in batch),
                "longitude": ",".join(str(p["longitude"]) for p in batch),
                "daily": "uv_index_clear_sky_max",
                "forecast_days": 2,
                "timezone": "Asia/Bangkok",
            }
        )
        try:
            with fetch(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=20) as response:
                payload = json.load(response)
            if not isinstance(payload, list) or len(payload) != len(batch):
                raise ValueError("Unexpected location count")
            for index, (province, location) in enumerate(zip(batch, payload, strict=True)):
                # Multi-location output follows input order; location_id also guards the mapping.
                if (
                    location.get("location_id", 0) != index
                    or location.get("timezone") != "Asia/Bangkok"
                ):
                    raise ValueError("Unexpected location or timezone")
                daily = location["daily"]
                values = daily["uv_index_clear_sky_max"]
                if daily["time"] != dates or len(values) != 2:
                    raise ValueError("Unexpected forecast dates")
                cached[province["id"]] = {
                    "generated_at": now.isoformat(),
                    "days": [
                        {"date": day, "uv_index": value if valid_uv(value) else None}
                        for day, value in zip(dates, values, strict=True)
                    ],
                }
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            failures += 1
            print(f"UV map batch {start // 20 + 1} unavailable ({type(error).__name__})")
    MAP_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temporary = MAP_SNAPSHOT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"provinces": cached}, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(MAP_SNAPSHOT)
    return failures


def load_map(day="today", now=None, *, source="api"):
    if day not in ("today", "tomorrow"):
        raise ValueError("Choose today or tomorrow")
    if source not in ("api", "model"):
        raise ValueError("Choose api or model")
    now = now or datetime.now(UTC)
    today = now.astimezone(ZoneInfo("Asia/Bangkok")).date()
    target = today + timedelta(days=day == "tomorrow")
    try:
        cached = json.loads(MAP_SNAPSHOT.read_text(encoding="utf-8"))["provinces"]
        if not isinstance(cached, dict):
            cached = {}
    except (OSError, ValueError, KeyError, TypeError):
        cached = {}
    results = []
    for province in PROVINCES:
        local = source == "model"
        if local and not province["model_city"]:
            continue
        result = {
            **province,
            "source": "local_model" if local else "open_meteo",
            "source_url": "https://temis.nl/uvradiation/UVarchive/stations_uv.php"
            if local
            else "https://open-meteo.com/",
            "aggregation": "solar_noon" if local else "daily_maximum",
            "date": target.isoformat(),
            "uv_index": None,
            "level": None,
            "status": "unavailable",
            "generated_at": None,
            "data_date": None,
            "model_version": None,
            "value_kind": "SARIMAX forecast" if local else "Open-Meteo forecast",
        }
        if local:
            try:
                prediction = load_recommendation(province["model_city"], now)
                entry = next(d for d in prediction["days"] if d["date"] == target.isoformat())
                if entry["value_kind"] != "SARIMAX forecast":
                    raise ValueError("Map requires a model prediction")
                result.update(
                    uv_index=entry["uv_index_clear_sky"],
                    level=entry["level"],
                    status="available",
                    generated_at=prediction["generated_at"],
                    data_date=prediction["data_date"],
                    model_version=prediction["model_version"],
                )
            except (ValueError, TypeError, KeyError, StopIteration):
                pass
        else:
            record = cached.get(province["id"], {})
            if not isinstance(record, dict):
                record = {}
            timestamp = record.get("generated_at")
            result["generated_at"] = timestamp if isinstance(timestamp, str) else None
            days = record.get("days", [])
            if not isinstance(days, list):
                days = []
            entry = next(
                (d for d in days if isinstance(d, dict) and d.get("date") == target.isoformat()), {}
            )
            if not fresh(timestamp, now):
                result["status"] = "stale" if timestamp else "unavailable"
            elif valid_uv(entry.get("uv_index")):
                result.update(
                    uv_index=entry["uv_index"],
                    level=uv_level(entry["uv_index"]),
                    status="available",
                )
        results.append(result)
    return {
        "date": target.isoformat(),
        "timezone": "Asia/Bangkok",
        "source": source,
        "provinces": results,
    }
