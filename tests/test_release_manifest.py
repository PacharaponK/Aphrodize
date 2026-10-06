"""Release inputs must be trusted, complete and immutable."""

import copy
import unittest

from scripts.release_manifest import validate_manifest, validate_origin

SHA = "a" * 40


def manifest():
    return {
        "schema_version": 1,
        "source_sha": SHA,
        "run_id": 42,
        "site_url": "https://aphrodize.duckdns.org",
        "images": {
            service: f"ghcr.io/pacharaponk/aphrodize-{service}@sha256:{'b' * 64}"
            for service in ("api", "frontend", "minio")
        },
    }


class ReleaseManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        self.assertEqual(validate_manifest(manifest()), manifest())

    def test_invalid_manifests(self):
        for key, value in (
            ("schema_version", 2),
            ("schema_version", True),
            ("source_sha", "main"),
            ("run_id", 0),
            ("run_id", True),
            ("site_url", "http://example.org"),
            ("site_url", "https://user:pass@example.org"),
            ("site_url", "https://example.org/path"),
            ("site_url", "https://example.org?token=secret"),
        ):
            with self.subTest(key=key, value=value):
                data = manifest()
                data[key] = value
                with self.assertRaises(ValueError):
                    validate_manifest(data)
        for image in (
            "evil.example/app@sha256:" + "b" * 64,
            "ghcr.io/pacharaponk/aphrodize-api:latest",
            "ghcr.io/pacharaponk/aphrodize-frontend@sha256:" + "b" * 64,
        ):
            data = manifest()
            data["images"]["api"] = image
            with self.assertRaises(ValueError):
                validate_manifest(data)
        data = manifest()
        del data["images"]["minio"]
        with self.assertRaises(ValueError):
            validate_manifest(data)

    def test_only_successful_current_main_push_is_trusted(self):
        run = {
            "event": "push",
            "head_branch": "main",
            "conclusion": "success",
            "head_sha": SHA,
            "name": "CI",
            "id": 42,
            "head_repository": {"full_name": "PacharaponK/Aphrodize"},
        }
        self.assertEqual(validate_origin(run, SHA), SHA)
        for key, value in (
            ("event", "pull_request"),
            ("head_branch", "dev"),
            ("conclusion", "failure"),
            ("conclusion", "cancelled"),
            ("head_sha", "main"),
            ("name", "Other"),
            ("head_repository", {"full_name": "fork/Aphrodize"}),
        ):
            bad = copy.deepcopy(run)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_origin(bad, SHA)
        with self.assertRaises(ValueError):
            validate_origin(run, "c" * 40)


if __name__ == "__main__":
    unittest.main()


def test_vm_rechecks_main_before_mutating_services(monkeypatch):
    import io
    import sys

    import pytest

    from scripts import release_manifest

    monkeypatch.setitem(sys.modules, "release_manifest", release_manifest)
    from scripts.deploy_vm import validate_current_main

    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: io.StringIO('{"sha":"' + SHA + '"}')
    )
    validate_current_main(SHA)
    with pytest.raises(RuntimeError, match="superseded"):
        validate_current_main("c" * 40)
