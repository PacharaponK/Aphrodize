"""Transactionally replace application containers, keeping private rollback state."""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from release_manifest import validate_manifest, validate_site_url

SOURCE = Path(__file__).resolve().parents[1]
OVERLAYS = {"compose.duckdns.yml", "compose.vm-worker-access.yml"}


class DeploymentError(RuntimeError):
    """An authored diagnostic safe to show in public Actions logs."""


def run(command, *, env=None, input_text=None, timeout=60):
    """Suppress tool output: Compose configuration can contain runtime secrets."""
    try:
        result = subprocess.run(
            command,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"{command[0]} unavailable or timed out") from exc
    if result.returncode:
        raise RuntimeError(f"{command[0]} operation failed (exit {result.returncode})")
    return result.stdout


def validate_current_main(source_sha):
    headers = {"User-Agent": "Aphrodize-release"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        "https://api.github.com/repos/PacharaponK/Aphrodize/commits/main", headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            current = json.load(response)["sha"]
    except Exception as exc:
        raise RuntimeError("Cannot verify current main; no services updated") from exc
    if current != source_sha:
        raise RuntimeError("Candidate superseded by newer main; no services updated")


def write_json(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    temp.chmod(0o600)
    temp.replace(path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class Deployment:
    def __init__(self, directory, overlays, ca_file):
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("Deployment directory must be an existing absolute path")
        self.directory = directory.resolve()
        self.overlays = [name for name in overlays.split(",") if name]
        if len(set(self.overlays)) != len(self.overlays) or set(self.overlays) - OVERLAYS:
            raise ValueError("Unsupported or duplicated Compose overlay")
        if not (self.directory / ".env").is_file():
            raise ValueError("Stable production .env is required")
        self.state = self.directory / ".releases"
        self.state.mkdir(mode=0o700, exist_ok=True)
        self.state.chmod(0o700)
        self.ca_file = ca_file
        if ca_file and not ca_file.is_file():
            raise ValueError("TLS CA file is missing")
        self.lock = (self.state / "deploy.lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another deployment holds the host lock") from exc

    def compose(self, files):
        command = [
            "docker",
            "compose",
            "--project-name",
            "aphrodize",
            "--project-directory",
            str(self.directory),
            "--env-file",
            str(self.directory / ".env"),
        ]
        for file in files:
            command += ["-f", str(file)]
        return command

    def stored(self, name):
        return self.state / name

    def record(self, name):
        value = json.loads(self.stored(name).read_text())
        path = Path(value["config"]).resolve()
        if not path.is_relative_to(self.state.resolve()) or not path.is_file():
            raise ValueError("Stored release configuration is missing or outside release state")
        validate_site_url(value["site_url"])
        return value

    def baseline(self):
        files = [self.directory / "compose.vm.yml"]
        files.extend(self.directory / name for name in self.overlays)
        if not all(file.is_file() for file in files):
            raise ValueError("Selected production Compose file is missing")
        config = json.loads(run(self.compose(files) + ["config", "--format", "json"]))
        for service in ("api", "frontend"):
            container = run(self.compose(files) + ["ps", "-q", service]).strip()
            if not container or "\n" in container:
                raise ValueError(f"Exactly one running {service} container is required")
            inspected = json.loads(run(["docker", "inspect", container]))[0]
            if inspected.get("State", {}).get("Health", {}).get("Status") != "healthy":
                raise ValueError(f"Baseline {service} is unhealthy")
            config["services"][service]["image"] = inspected["Image"]
        config["services"]["minio-init"]["image"] = config["services"]["api"]["image"]
        site_url = validate_site_url(config["services"]["frontend"]["environment"]["SITE_URL"])
        path = self.state / f"baseline-{time.time_ns()}.json"
        write_json(path, config)
        return {"config": str(path), "site_url": site_url, "manifest": None}

    def health(self, record):
        command = self.compose([record["config"]])
        for service in ("api", "frontend"):
            container = run(command + ["ps", "-q", service]).strip()
            if not container or "\n" in container:
                raise RuntimeError(f"Missing {service} container")
            inspected = json.loads(run(["docker", "inspect", container]))[0]
            if inspected.get("State", {}).get("Health", {}).get("Status") != "healthy":
                raise RuntimeError(f"Unhealthy {service} container")
        probe = (SOURCE / "scripts/check-vm-readiness.py").read_text()
        run(command + ["exec", "-T", "api", "python", "-"], input_text=probe, timeout=45)
        curl = [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--connect-timeout",
            "10",
            "--max-time",
            "30",
            "--output",
            "/dev/null",
        ]
        if self.ca_file:
            curl += ["--cacert", str(self.ca_file)]
        run(curl + [record["site_url"].rstrip("/") + "/login"], timeout=35)

    def update(self, record):
        command = self.compose([record["config"]])
        run(command + ["run", "--rm", "--no-deps", "--pull", "never", "minio-init"], timeout=180)
        run(
            command
            + [
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--wait",
                "--wait-timeout",
                "180",
                "api",
                "frontend",
            ],
            timeout=240,
        )
        self.health(record)

    def restore(self, previous):
        self.update(previous)
        write_json(self.stored("current-release.json"), previous)
        pending_file = self.stored("pending-release.json")
        if pending_file.exists():
            pending = json.loads(pending_file.read_text())
            history = pending.get("rollback_previous")
            if history is None:
                self.stored("previous-release.json").unlink(missing_ok=True)
            else:
                write_json(self.stored("previous-release.json"), history)
        pending_file.unlink(missing_ok=True)

    def deploy(self, manifest, verify_main=False):
        if self.stored("pending-release.json").exists():
            raise RuntimeError("Unfinished deployment: use --recover before another release")
        if verify_main:
            validate_current_main(manifest["source_sha"])
        previous = (
            self.record("current-release.json")
            if self.stored("current-release.json").exists()
            else self.baseline()
        )
        if manifest["site_url"].rstrip("/") != previous["site_url"].rstrip("/"):
            raise ValueError("Release SITE_URL does not match current production origin")
        # Do not advance any pointer if a pull or config preflight fails.
        for service in ("api", "frontend"):
            run(["docker", "pull", manifest["images"][service]], timeout=600)
        files = [SOURCE / "compose.vm.yml"]
        files.extend(self.directory / name for name in self.overlays)
        files.append(SOURCE / "compose.release.yml")
        env = {
            **os.environ,
            "API_IMAGE": manifest["images"]["api"],
            "FRONTEND_IMAGE": manifest["images"]["frontend"],
        }
        config = json.loads(run(self.compose(files) + ["config", "--format", "json"], env=env))
        old_config = json.loads(Path(previous["config"]).read_text())
        # Runtime integrations live in the VM configuration, separately from images.
        # Reject releases that silently drop a configured annotation workflow.
        runtime_files = [self.directory / "compose.vm.yml"]
        runtime_files.extend(self.directory / name for name in self.overlays)
        runtime_config = json.loads(
            run(self.compose(runtime_files) + ["config", "--format", "json"])
        )
        runtime_env = runtime_config["services"]["api"].get("environment", {})
        candidate_env = config["services"]["api"].get("environment", {})
        if runtime_env.get("LABEL_STUDIO_API_KEY") and int(
            runtime_env.get("LABEL_STUDIO_PROJECT_ID", 0)
        ) > 0:
            if any(
                candidate_env.get(key) != runtime_env.get(key)
                for key in (
                    "LABEL_STUDIO_URL", "LABEL_STUDIO_API_KEY", "LABEL_STUDIO_PROJECT_ID"
                )
            ):
                raise DeploymentError(
                    "Release drops or changes the VM annotation review configuration; "
                    "no services updated"
                )
        for service in ("postgres", "redis", "minio", "caddy"):
            if config["services"].get(service) != old_config["services"].get(service):
                raise ValueError(f"Infrastructure change in {service} needs a separate deployment")
        # Optional VM services can declare volumes absent from the release source.
        # Keep their declarations, but reject new or changed release volume mappings.
        old_volumes = old_config.get("volumes", {})
        release_volumes = config.get("volumes", {})
        if any(
            name not in old_volumes or value != old_volumes[name]
            for name, value in release_volumes.items()
        ):
            raise DeploymentError(
                "Persistent volume configuration changed; explicit migration required"
            )
        if old_volumes:
            config["volumes"] = {**old_volumes, **release_volumes}
        for service in ("api", "frontend"):
            if config["services"][service].get("volumes") != old_config["services"][service].get(
                "volumes"
            ):
                raise ValueError(f"Bind/volume changes in {service} need explicit migration")
        origin = config["services"]["frontend"]["environment"]["SITE_URL"]
        if validate_site_url(origin) != manifest["site_url"].rstrip("/"):
            raise ValueError("Rendered frontend origin does not match the manifest")
        path = self.state / f"candidate-{manifest['source_sha']}-{time.time_ns()}.json"
        write_json(path, config)
        candidate = {"config": str(path), "site_url": manifest["site_url"], "manifest": manifest}
        if verify_main:
            validate_current_main(manifest["source_sha"])
        write_json(self.stored("current-release.json"), previous)
        history = (
            self.record("previous-release.json")
            if self.stored("previous-release.json").exists()
            else None
        )
        write_json(
            self.stored("pending-release.json"),
            {"previous": previous, "candidate": candidate, "rollback_previous": history},
        )
        try:
            self.update(candidate)
            write_json(self.stored("previous-release.json"), previous)
            write_json(self.stored("current-release.json"), candidate)
            self.stored("pending-release.json").unlink()
        except (Exception, KeyboardInterrupt) as failure:
            # Prevent a second termination signal from interrupting recovery.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                self.restore(previous)
            except Exception as rollback:
                print(
                    f"Rollback failed: {rollback}. Retained pending state; use --recover.",
                    file=sys.stderr,
                )
            else:
                print("Rollback succeeded; candidate deployment failed.", file=sys.stderr)
            raise RuntimeError(f"Candidate failed: {failure}") from failure
        print(f"Deployed {manifest['source_sha']}")

    def recover(self):
        pending = json.loads(self.stored("pending-release.json").read_text())
        previous = pending["previous"]
        path = Path(previous["config"]).resolve()
        if not path.is_relative_to(self.state.resolve()) or not path.is_file():
            raise ValueError("Invalid recovery configuration")
        validate_site_url(previous["site_url"])
        self.restore(previous)
        print("Recovery succeeded")

    def rollback(self):
        current = self.record("current-release.json")
        previous = self.record("previous-release.json")
        if self.stored("pending-release.json").exists():
            raise RuntimeError("Unfinished deployment: use --recover")
        write_json(
            self.stored("pending-release.json"),
            {"previous": current, "candidate": previous, "rollback_previous": previous},
        )
        self.update(previous)
        write_json(self.stored("current-release.json"), previous)
        write_json(self.stored("previous-release.json"), current)
        self.stored("pending-release.json").unlink()
        print("Manual rollback succeeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--manifest", type=Path)
    mode.add_argument("--recover", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--deploy-dir", type=Path, required=True)
    parser.add_argument("--overlays", default="")
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--verify-main", action="store_true")
    args = parser.parse_args()

    def terminate(_signal, _frame):
        raise RuntimeError("Deployment interrupted; rollback/recovery required")

    signal.signal(signal.SIGTERM, terminate)
    os.umask(0o077)
    try:
        manifest = (
            validate_manifest(json.loads(args.manifest.read_text())) if args.manifest else None
        )
        deployment = Deployment(args.deploy_dir, args.overlays, args.ca_file)
        if manifest:
            deployment.deploy(manifest, verify_main=args.verify_main)
        elif args.recover:
            deployment.recover()
        else:
            deployment.rollback()
    except DeploymentError as exc:
        print(f"Deployment failed: {exc}", file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        # Keep exception chains/config content out of public Actions logs.
        print(
            "Deployment failed; inspect protected local release state and job outcome.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
