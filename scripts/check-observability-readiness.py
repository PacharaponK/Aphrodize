"""Check authenticated API telemetry inside the release image without printing secrets."""

import base64
import time
from urllib.request import Request, urlopen

from backend.core.config import settings


def check_metrics(metrics):
    values = dict(
        line.split()
        for line in metrics.splitlines()
        if line.startswith(
            ("aphrodize_collector_success ", "aphrodize_collector_timestamp_seconds ")
        )
    )
    assert float(values["aphrodize_collector_success"]) == 1
    assert -5 <= time.time() - float(values["aphrodize_collector_timestamp_seconds"]) <= 120


def check():
    assert settings.observability_enabled
    credentials = base64.b64encode(
        f"{settings.api_username}:{settings.api_password}".encode()
    ).decode()
    request = Request(
        "http://127.0.0.1:8000/api/v1/monitoring/metrics",
        headers={"Authorization": "Basic " + credentials},
    )
    # Older rollback images reset success while a collection is still in progress.
    for attempt in range(6):
        try:
            with urlopen(request, timeout=2) as response:
                check_metrics(response.read().decode())
            return
        except Exception:
            if attempt == 5:
                raise
            time.sleep(1)


if __name__ == "__main__":
    try:
        check()
    except Exception:
        raise SystemExit("API observability readiness check failed") from None
