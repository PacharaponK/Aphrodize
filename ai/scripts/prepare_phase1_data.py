"""Download and verify the FFHQ images listed by the official test split."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from ai.ffhq_wrinkle.paths import DATA_ROOT

MIRROR_REPOSITORY = "marcosv/ffhq-dataset"
MIRROR_REVISION = "505f94e2ecc6db64e967e8e6c8e2c2079ea0876b"
MIRROR_BASE_URL = f"https://huggingface.co/datasets/{MIRROR_REPOSITORY}/resolve/{MIRROR_REVISION}"

DEFAULT_DATA_ROOT = DATA_ROOT
DEFAULT_TEST_IDS = DEFAULT_DATA_ROOT / "test_file_lists.txt"
DEFAULT_MANIFEST = DEFAULT_DATA_ROOT / "phase1_test_images.json"


def read_image_ids(path: Path) -> list[str]:
    image_ids = [
        line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    invalid = [image_id for image_id in image_ids if len(image_id) != 5 or not image_id.isdigit()]
    if invalid:
        raise ValueError(f"invalid FFHQ image IDs: {invalid}")
    if len(image_ids) != len(set(image_ids)):
        raise ValueError("duplicate FFHQ image IDs")
    return image_ids


def image_location(image_id: str, data_root: Path) -> tuple[str, Path]:
    number = int(image_id)
    part = number // 10_000 + 1
    ffhq_group = number - number % 1_000
    url = f"{MIRROR_BASE_URL}/Part{part}/{image_id}.png"
    destination = data_root / "images1024x1024" / f"{ffhq_group:05d}" / f"{image_id}.png"
    return url, destination


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download_image(image_id: str, data_root: Path, timeout: float) -> dict[str, Any]:
    url, destination = image_location(image_id, data_root)
    with requests.Session() as session:
        metadata_response = session.get(url, allow_redirects=False, timeout=timeout)
        metadata_response.raise_for_status()
        if not metadata_response.is_redirect:
            raise RuntimeError(f"mirror did not return LFS metadata redirect for {image_id}")

        expected_hash = metadata_response.headers.get("X-Linked-ETag", "").strip('"').lower()
        expected_size_text = metadata_response.headers.get("X-Linked-Size")
        if len(expected_hash) != 64 or not expected_size_text:
            raise RuntimeError(f"mirror omitted LFS integrity metadata for {image_id}")
        expected_size = int(expected_size_text)

        if destination.is_file():
            actual_hash = sha256_file(destination)
            actual_size = destination.stat().st_size
            if actual_hash == expected_hash and actual_size == expected_size:
                return {
                    "id": image_id,
                    "path": destination.as_posix(),
                    "bytes": actual_size,
                    "sha256": actual_hash,
                    "status": "verified-existing",
                }
            raise RuntimeError(f"existing image failed integrity verification: {destination}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{image_id}.", suffix=".part", dir=destination.parent, delete=False
        ) as temp_stream:
            temp_path = Path(temp_stream.name)
            digest = hashlib.sha256()
            actual_size = 0
            try:
                with session.get(
                    metadata_response.headers["Location"], stream=True, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            temp_stream.write(chunk)
                            digest.update(chunk)
                            actual_size += len(chunk)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise

        actual_hash = digest.hexdigest()
        if actual_size != expected_size or actual_hash != expected_hash:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"downloaded image failed integrity verification: {image_id} "
                f"({actual_size} bytes, {actual_hash})"
            )
        os.replace(temp_path, destination)
        return {
            "id": image_id,
            "path": destination.as_posix(),
            "bytes": actual_size,
            "sha256": actual_hash,
            "status": "downloaded",
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-ids", type=Path, default=DEFAULT_TEST_IDS)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.workers < 1:
        raise ValueError("workers must be at least 1")
    image_ids = read_image_ids(args.test_ids)
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_image, image_id, args.data_root, args.timeout): image_id
            for image_id in image_ids
        }
        for completed, future in enumerate(as_completed(futures), 1):
            record = future.result()
            records.append(record)
            print(f"[{completed}/{len(image_ids)}] {record['id']} {record['status']}")

    records.sort(key=lambda item: item["id"])
    manifest = {
        "source": {
            "repository": MIRROR_REPOSITORY,
            "revision": MIRROR_REVISION,
            "base_url": MIRROR_BASE_URL,
        },
        "test_ids_file": args.test_ids.as_posix(),
        "count": len(records),
        "images": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(records)} images; manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
