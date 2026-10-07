"""Run on an independent host; send Discord outage/recovery transitions."""

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def validate_urls(target, webhook):
    url = urlsplit(target)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query:
        raise ValueError("Probe target must be HTTPS without credentials or query parameters")
    hook = urlsplit(webhook)
    if (
        hook.scheme != "https"
        or hook.hostname != "discord.com"
        or not hook.path.startswith("/api/webhooks/")
        or hook.username
        or hook.password
    ):
        raise ValueError("Use a Discord HTTPS webhook")


def probe(target):
    try:
        with urlopen(target, timeout=5) as response:
            return response.status == 200 and json.loads(response.read(1024)).get("status") == "ok"
    except Exception:
        return False


def notify(webhook, state):
    payload = {
        "content": f"Aphrodize external probe: {state} at {datetime.now(UTC).isoformat()}",
        "allowed_mentions": {"parse": []},
    }
    request = Request(
        webhook,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Aphrodize/1"},
    )
    with urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError("Notification delivery failed")


def advance(state, healthy, now):
    """Return a pending transition; four failed 30s probes are ~2 minutes."""
    state["failures"] = 0 if healthy else state.get("failures", 0) + 1
    if not healthy and state.get("pending") == "recovered":
        state.pop("pending", None)
    if healthy and state.get("notified") == "down":
        state["pending"] = "recovered"
    elif not healthy and state["failures"] >= 4 and state.get("notified") != "down":
        state["pending"] = "down"
    elif healthy and state.get("notified") != "down":
        state.pop("pending", None)
    state["checked_at"] = now
    return state.get("pending")


def main():
    target, webhook = os.environ["PROBE_URL"], os.environ["DISCORD_WEBHOOK_URL"]
    validate_urls(target, webhook)
    path = Path(os.getenv("PROBE_STATE_FILE", "/state/probe.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        state = {}
    while True:
        pending = advance(state, probe(target), time.time())
        if pending:
            try:
                notify(webhook, pending)
                state["notified"] = "down" if pending == "down" else "up"
                state.pop("pending", None)
            except Exception:
                # Retry delivery next tick. Never print a webhook or exception message.
                logging.warning("Discord notification delivery failed")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state))
        temporary.replace(path)
        time.sleep(30)


if __name__ == "__main__":
    main()
