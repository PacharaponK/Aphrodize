"""Render private scrape credentials and optional targets without printing secrets."""

import argparse
import json
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def configure(env, output):
    if not env.get("API_PASSWORD"):
        raise ValueError("API_PASSWORD is required")
    queues = {q.strip() for q in env.get("OBS_EXPECTED_QUEUES", "").split(",") if q.strip()}
    if not queues <= {"inference", "training"}:
        raise ValueError("OBS_EXPECTED_QUEUES must contain inference and/or training")
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    config = yaml.safe_load((ROOT / "docker/observability/prometheus.yml").read_text())
    config["scrape_configs"][0]["basic_auth"]["username"] = env.get("API_USERNAME", "aphrodize")
    (output / "prometheus.yml").write_text(yaml.safe_dump(config, sort_keys=False))
    secret = output / "api-password"
    secret.write_text(env["API_PASSWORD"], encoding="utf-8")
    # Prometheus runs as nobody; restrict the parent and mount only this file read-only.
    secret.chmod(0o644)
    targets = output / "targets"
    targets.mkdir(exist_ok=True)
    workers = []
    for queue in sorted(queues):
        address = env.get(f"OBS_{queue.upper()}_TARGET", f"{queue}-worker:9101")
        workers.append({"targets": [address], "labels": {"queue": queue}})
    gpu = [{"targets": [env["OBS_GPU_TARGET"]]}] if env.get("OBS_GPU_TARGET") else []
    caddy = [{"targets": ["caddy:9100"]}] if env.get("OBS_CADDY_ENABLED") == "true" else []
    probes = [{"targets": ["http://api:8000/api/v1/health"], "labels": {"service": "api"}}]
    if env.get("OBS_FRONTEND_ENABLED") == "true":
        probes.append(
            {"targets": ["http://frontend:3000/api/health"], "labels": {"service": "frontend"}}
        )
    for name, values in {"workers": workers, "gpu": gpu, "caddy": caddy, "probes": probes}.items():
        (targets / f"{name}.json").write_text(json.dumps(values) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    env = {**dotenv_values(args.env_file), **os.environ}
    configure(env, ROOT / ".observability")
    print("Rendered private scrape configuration and optional targets.")
    if not env.get("DISCORD_WEBHOOK_URL"):
        print("Alert delivery is not configured: set DISCORD_WEBHOOK_URL before operational use.")


if __name__ == "__main__":
    main()
