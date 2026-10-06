"""Bind saved forecasts to server inference, never to browser-supplied scores."""
from datetime import UTC, date, datetime, timedelta
from typing import Any

import jwt

from backend.core.config import settings

AUDIENCE = "daily-health-observed-forecast"


def issue_forecast_receipt(result: dict[str, Any]) -> str | None:
    if result.get("model_status") != "experimental_user_reported_candidate":
        return None
    signals = {
        key: signal for key, signal in result["interpretation"]["next_day_predictions"].items()
        if signal.get("status") == "predicted"
    }
    if not signals:
        return None
    values = result["input"]
    now = datetime.now(UTC)
    return jwt.encode({
        "aud": AUDIENCE, "iat": now, "exp": now + timedelta(hours=2),
        "local_date": result["local_date"],
        "inputs": [values["sleep_duration_total_minutes"], values["water_intake_ml"],
                   values["outdoor_exposure_choice"]],
        "signals": signals,
    }, settings.jwt_secret_key, algorithm="HS256")


def verify_forecast_receipt(
    receipt: str, *, local_date: date, sleep_minutes: int, water_ml: int, outdoors: int,
) -> dict[str, Any]:
    """Reject expired/tampered receipts and edits to the inputs after inference."""
    try:
        claims = jwt.decode(receipt, settings.jwt_secret_key, algorithms=["HS256"],
                            audience=AUDIENCE, options={"require": ["exp", "iat", "aud"]})
        if (claims["local_date"] != local_date.isoformat()
                or claims["inputs"] != [sleep_minutes, water_ml, outdoors]):
            raise ValueError("Forecast inputs do not match the saved day")
        signals = claims["signals"]
        expected_date = (local_date + timedelta(days=1)).isoformat()
        if not isinstance(signals, dict) or not signals:
            raise ValueError("Missing forecast signals")
        for key, signal in signals.items():
            if (key not in {"thirst_attention", "low_energy_signal"}
                    or signal.get("target_date") != expected_date
                    or signal.get("status") != "predicted"
                    or signal.get("method") != "user_reported_next_day_model"
                    or not isinstance(signal.get("value_0_10"), float | int)
                    or not 0 <= signal["value_0_10"] <= 10):
                raise ValueError("Invalid forecast signal")
        return signals
    except (jwt.PyJWTError, KeyError, TypeError, AttributeError) as error:
        raise ValueError("Invalid or expired forecast receipt") from error
