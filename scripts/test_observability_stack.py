"""Isolated Docker check: provisioning, scrapes, safe logs, firing/recovery, persistence."""

import argparse
import asyncio
import base64
import json
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from scripts.configure_observability import configure

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "aphrodize-observability-check"


async def check_arq():
    from arq import create_pool, func
    from arq.connections import RedisSettings
    from arq.worker import Worker

    from backend.core.observability import enqueue_job, observed_job, request_id

    @observed_job
    async def correlation_check(ctx):
        return request_id.get()

    pool = await create_pool(RedisSettings(host="127.0.0.1", port=16390))
    worker = Worker(
        [func(correlation_check, name="correlation_check")],
        redis_pool=pool,
        queue_name="inference",
        burst=True,
        handle_signals=False,
        log_results=False,
    )
    try:
        token = request_id.set("f" * 32)
        try:
            job = await enqueue_job(pool, "correlation_check", _queue_name="inference")
        finally:
            request_id.reset(token)
        await worker.async_run()
        assert await job.result(timeout=2) == "f" * 32
        assert request_id.get() == ""
        print("PASS real Redis/ARQ correlation round trip", flush=True)
    finally:
        await pool.aclose()


def request(url, auth=None):
    headers = {"Authorization": f"Basic {auth}"} if auth else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return response.read().decode()


def wait_for(check, description, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                print(f"PASS {description}", flush=True)
                return
        except AssertionError:
            raise
        except Exception:
            pass
        time.sleep(5)
    raise AssertionError(f"Timed out: {description}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="Shorten only synthetic alert timers")
    options = parser.parse_args()
    output = ROOT / ".observability/smoke"
    output.mkdir(parents=True, exist_ok=True)
    configure({"API_PASSWORD": "synthetic-only"}, output)
    source = yaml.safe_load((ROOT / "compose.observability.yml").read_text())
    services = source["services"]
    selected = {
        name: services[name]
        for name in ("prometheus", "loki", "docker-socket-proxy", "alloy", "grafana", "blackbox")
    }
    password = secrets.token_hex(16)
    for service in selected.values():
        # Resolve source mounts; keep synthetic scrape credentials separate from deployment.
        volumes = []
        for mount in service.get("volumes", []):
            if mount.startswith("./.observability/"):
                mount = mount.replace("./.observability/", output.as_posix() + "/", 1)
            elif mount.startswith("./"):
                mount = ROOT.as_posix() + mount[1:]
            volumes.append(mount)
        service["volumes"] = volumes
    selected["prometheus"]["ports"] = ["127.0.0.1:39090:9090"]
    selected["loki"]["ports"] = ["127.0.0.1:33100:3100"]
    selected["grafana"]["ports"] = ["127.0.0.1:33001:3000"]
    selected["grafana"]["environment"].update(
        {
            "GF_SECURITY_ADMIN_USER": "admin",
            "GF_SECURITY_ADMIN_PASSWORD": password,
            "GF_SERVER_ROOT_URL": "http://127.0.0.1:33001",
            "DISCORD_WEBHOOK_URL": "http://api:8000/discord",
        }
    )
    if options.fast:
        provisioned = output / "grafana"
        shutil.copytree(ROOT / "docker/observability/grafana", provisioned, dirs_exist_ok=True)
        rules_path = provisioned / "alerting/rules.yml"
        rules = yaml.safe_load(rules_path.read_text())
        for group in rules["groups"]:
            group["interval"] = "10s"
            for rule in group["rules"]:
                rule["for"] = "5s"
        rules_path.write_text(yaml.safe_dump(rules, sort_keys=False))
        contacts_path = provisioned / "alerting/contact.yml"
        contacts = yaml.safe_load(contacts_path.read_text())
        contacts["policies"][0].update({"group_wait": "1s", "group_interval": "10s"})
        contacts_path.write_text(yaml.safe_dump(contacts, sort_keys=False))
        selected["grafana"]["volumes"][0] = f"{provisioned.as_posix()}:/etc/grafana/provisioning:ro"
    selected["alloy"]["environment"].update(
        {"OBS_ENVIRONMENT": "test", "OBS_HOST": "smoke", "OBS_PROJECT": PROJECT}
    )
    # Do not collect another Compose project's application logs.
    alloy = (ROOT / "docker/observability/config.alloy").read_text()
    alloy = alloy.replace(
        "targets = discovery.docker.services.targets",
        "targets = discovery.docker.services.targets\n  rule {\n"
        '    source_labels = ["__meta_docker_container_label_com_docker_compose_project"]\n'
        f'    regex = "{PROJECT}"\n    action = "keep"\n  }}',
    )
    (output / "config.alloy").write_text(alloy)
    selected["alloy"]["volumes"][0] = f"{output.as_posix()}/config.alloy:/etc/alloy/config.alloy:ro"
    selected["api"] = {
        "image": "python:3.11-alpine",
        "command": "python /app/fixture.py",
        "volumes": [f"{ROOT.as_posix()}/tests/observability_fixture.py:/app/fixture.py:ro"],
        "ports": ["127.0.0.1:38000:8000"],
        "logging": {"driver": "local", "options": {"max-size": "5m", "max-file": "2"}},
    }
    selected["redis"] = {"image": "redis:7-alpine", "ports": ["127.0.0.1:16390:6379"]}
    data = {
        "name": PROJECT,
        "services": selected,
        "networks": source["networks"],
        "volumes": source["volumes"],
    }
    compose = output / "compose.yml"
    compose.write_text(yaml.safe_dump(data, sort_keys=False))
    args = ["docker", "compose", "-p", PROJECT, "-f", str(compose)]
    auth = base64.b64encode(f"admin:{password}".encode()).decode()

    def docker(*command):
        subprocess.run([*args, *command], check=True)

    try:
        docker("up", "-d")
        asyncio.run(check_arq())
        wait_for(
            lambda: json.loads(request("http://127.0.0.1:33001/api/health"))["database"] == "ok",
            "Grafana started and provisioned",
        )
        wait_for(
            lambda: len(
                json.loads(request("http://127.0.0.1:33001/api/v1/provisioning/alert-rules", auth))
            )
            >= 14,
            "Alert provisioning completed",
        )
        rules = json.loads(request("http://127.0.0.1:33001/api/v1/provisioning/alert-rules", auth))
        for rule in rules:
            result = json.loads(
                request(
                    "http://127.0.0.1:39090/api/v1/query?"
                    + urlencode({"query": rule["data"][0]["model"]["expr"]})
                )
            )
            assert result["status"] == "success"
        wait_for(
            lambda: len(json.loads(request("http://127.0.0.1:33001/api/search?type=dash-db", auth)))
            == 3,
            "Dashboard provisioning completed",
        )
        print("PASS three dashboards and alert rules provisioned", flush=True)
        query = 'up{job="api"}'
        wait_for(
            lambda: json.loads(
                request("http://127.0.0.1:39090/api/v1/query?" + urlencode({"query": query}))
            )["data"]["result"][0]["value"][1]
            == "1",
            "Prometheus scraped API",
        )
        request("http://127.0.0.1:38000/api/v1/health")

        def logs_received():
            value = json.loads(
                request(
                    "http://127.0.0.1:33100/loki/api/v1/query_range?"
                    + urlencode({"query": '{service="api"} |= "smoke_probe"', "limit": 100})
                )
            )
            results = value["data"]["result"]
            if not results:
                return False
            assert "PRIVATE_SENTINEL" not in json.dumps(results)
            assert "d" * 32 in json.dumps(results)
            return True

        wait_for(logs_received, "Docker local-driver logs reach Loki with private fields removed")
        request("http://127.0.0.1:38000/fault")
        wait_for(
            lambda: any(
                "Required dependency unavailable" in json.dumps(n)
                for n in json.loads(request("http://127.0.0.1:38000/notifications"))
            ),
            "Discord-format firing notification delivered to local receiver",
            timeout=300,
        )
        request("http://127.0.0.1:38000/recover")
        wait_for(
            lambda: any(
                "Required dependency unavailable" in json.dumps(n)
                and ("Resolved" in json.dumps(n) or "RESOLVED" in json.dumps(n))
                for n in json.loads(request("http://127.0.0.1:38000/notifications"))
            ),
            "Recovery notification delivered",
            timeout=390,
        )
        docker("restart", "grafana", "loki", "prometheus", "alloy")
        wait_for(
            lambda: len(json.loads(request("http://127.0.0.1:33001/api/search?type=dash-db", auth)))
            == 3,
            "Dashboard/config survive restart",
        )
        wait_for(logs_received, "Stored logs survive restart")
        print("PASS isolated observability integration", flush=True)
    finally:
        # Only this explicitly named, synthetic project owns these disposable volumes.
        docker("down", "--volumes")


if __name__ == "__main__":
    main()
