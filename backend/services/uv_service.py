"""Read validated local UV snapshots and turn their values into cautious protection advice."""

import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SNAPSHOT = Path(__file__).resolve().parents[2] / "storage/artifacts/uv/forecast_snapshot.json"


def uv_level(value: float) -> str:
    if value < 3:
        return "low"
    if value < 6:
        return "moderate"
    if value < 8:
        return "high"
    if value < 11:
        return "very_high"
    return "extreme"


def load_recommendation(city: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    today = now.astimezone(ZoneInfo("Asia/Bangkok")).date()
    try:
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        generated = datetime.fromisoformat(snapshot["generated_at"])
        selected = snapshot["cities"][city]
        data_date = date.fromisoformat(selected["data_date"])
        days = selected["days"]
        source = snapshot["source"]
        model_version = selected["model_version"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("UV forecast snapshot is unavailable or invalid") from error
    if generated.tzinfo is None or not -timedelta(minutes=5) <= now - generated <= timedelta(
        hours=8
    ):
        raise ValueError("UV forecast has not been refreshed in eight hours")
    if not today - timedelta(days=1) <= data_date <= today:
        raise ValueError("TEMIS UV data are older than yesterday")
    if (
        not isinstance(days, list)
        or len(days) != 2
        or any(
            not isinstance(entry, dict)
            or not {"date", "uv_index_clear_sky", "value_kind", "weather"} <= entry.keys()
            for entry in days
        )
    ):
        raise ValueError("UV forecast days are invalid")
    if [entry["date"] for entry in days] != [
        today.isoformat(),
        (today + timedelta(days=1)).isoformat(),
    ]:
        raise ValueError("UV forecast dates do not match today and tomorrow")
    for entry in days:
        value = entry["uv_index_clear_sky"]
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            or not 0 <= value <= 25
        ):
            raise ValueError("UV forecast contains an invalid value")
        entry["level"] = uv_level(value)
        entry["priority"] = (
            "avoid_midday" if value >= 8 else "seek_midday_shade" if value >= 3 else "routine"
        )
    return {
        "city": city,
        "data_date": selected["data_date"],
        "generated_at": snapshot["generated_at"],
        "model_version": model_version,
        "source": source,
        "days": days,
        "advice": {
            "product_type": "Broad-spectrum sunscreen SPF 30 or higher",
            "application": (
                "Apply generously to exposed skin before going outdoors; "
                "follow the label for amount and timing."
            ),
            "reapplication": (
                "Reapply at least every two hours outdoors and after swimming, "
                "sweating, or towel drying; follow the label."
            ),
            "other_protection": (
                "Seek shade, wear protective clothing, a broad-brimmed hat "
                "and sunglasses, especially around midday."
            ),
            "caveat": (
                "These are clear-sky UV estimates at local solar noon, not "
                "measured all-sky UV or personal exposure. Clouds can still allow high UV."
            ),
            "source_url": "https://www.who.int/news-room/questions-and-answers/item/radiation-protecting-against-skin-cancer",
        },
    }
