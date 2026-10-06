"""Validate immutable releases and the CI run that produced them (stdlib only)."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY = "PacharaponK/Aphrodize"
SERVICES = ("api", "frontend", "minio")
SHA = re.compile(r"[0-9a-f]{40}")


def validate_site_url(value: object) -> str:
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError("SITE_URL must be an HTTPS origin")
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ValueError("SITE_URL must be an HTTPS origin without credentials or path")
    try:
        port = url.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("Invalid port")
    except ValueError as exc:
        raise ValueError("Invalid SITE_URL port") from exc
    return value.rstrip("/")


def validate_manifest(data: dict) -> dict:
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError("Unsupported manifest schema")
    if not isinstance(data.get("source_sha"), str) or not SHA.fullmatch(data["source_sha"]):
        raise ValueError("Expected a full commit SHA")
    if type(data.get("run_id")) is not int or data["run_id"] <= 0:
        raise ValueError("Invalid workflow run ID")
    validate_site_url(data.get("site_url"))
    images = data.get("images")
    if not isinstance(images, dict) or set(images) != set(SERVICES):
        raise ValueError("Release requires exactly API, frontend and MinIO images")
    for service, reference in images.items():
        pattern = rf"ghcr\.io/pacharaponk/aphrodize-{service}@sha256:[0-9a-f]{{64}}"
        if not isinstance(reference, str) or not re.fullmatch(pattern, reference):
            raise ValueError(f"Invalid {service} image digest reference")
    return data


def validate_origin(run: dict, main_sha: str) -> str:
    if (
        run.get("event") != "push"
        or run.get("head_branch") != "main"
        or run.get("conclusion") != "success"
        or run.get("name") != "CI"
        or run.get("head_repository", {}).get("full_name") != REPOSITORY
    ):
        raise ValueError("Release requires successful CI from this repository's main push")
    tested = run.get("head_sha")
    if not isinstance(tested, str) or not SHA.fullmatch(tested) or tested != main_sha:
        raise ValueError("Candidate is invalid or superseded by current main")
    return tested


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    origin = sub.add_parser("origin")
    origin.add_argument("--event-file", type=Path, required=True)
    origin.add_argument("--current-sha", required=True)
    manifest = sub.add_parser("validate")
    manifest.add_argument("file", type=Path)
    manifest.add_argument("--source-sha")
    manifest.add_argument("--run-id", type=int)
    args = parser.parse_args()
    try:
        if args.command == "origin":
            print(
                validate_origin(
                    json.loads(args.event_file.read_text())["workflow_run"], args.current_sha
                )
            )
        else:
            data = validate_manifest(json.loads(args.file.read_text()))
            if args.source_sha and data["source_sha"] != args.source_sha:
                raise ValueError("Manifest source SHA mismatch")
            if args.run_id and data["run_id"] != args.run_id:
                raise ValueError("Manifest workflow run mismatch")
            print(data["source_sha"])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")


if __name__ == "__main__":
    main()
