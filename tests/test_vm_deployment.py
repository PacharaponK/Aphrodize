"""Exercise actual deploy CLI against disposable fake Docker and curl binaries."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "b" * 64
FAKE_DOCKER = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
state = Path(os.environ['FAKE_STATE'])
with (state / 'commands.jsonl').open('a') as f: f.write(json.dumps(args)+'\\n')
mode = os.environ.get('FAKE_MODE', '')
if args[:1] == ['inspect']:
 status = 'unhealthy' if mode == 'baseline-unhealthy' else 'healthy'
 print(json.dumps([{'Image': 'sha256:'+'a'*64, 'State': {'Health': {'Status': status}}}]))
if 'config' in args:
 root = os.environ['FAKE_DEPLOY_DIR']
 volumes = {'postgres_data':{'name':'aphrodize_postgres_data'}}
 candidate = 'API_IMAGE' in os.environ
 if mode == 'extra-vm-volume' and not candidate:
  volumes['label_studio_data'] = {'name':'aphrodize_label_studio_data'}
 if mode == 'changed-volume' and candidate:
  volumes['postgres_data']['name'] = 'private-not-for-logs'
 if mode == 'new-volume' and candidate:
  volumes['new_data'] = {'name':'new_data'}
 config = {'name':'aphrodize', 'services': {
 'api': {'image':os.environ.get('API_IMAGE','old-api'),
 'volumes':[{'type':'bind','source':root+'/storage/artifacts/uv',
 'target':'/app/storage/artifacts/uv'}]},
 'frontend': {'image':os.environ.get('FRONTEND_IMAGE','old-web'), 'environment':{'SITE_URL':'https://aphrodize.duckdns.org'}},
 'minio-init': {'image':os.environ.get('API_IMAGE','old-api')},
 'postgres': {'image':'postgres:16-alpine'},
 'caddy': {'image':'caddy:2-alpine', 'volumes':[{'type':'bind','source':root+'/docker/Caddyfile.vm',
 'target':'/etc/caddy/Caddyfile'}]},
 }, 'volumes':volumes}
 if mode.startswith('monitoring'):
  config['services']['api']['environment'] = {'OBSERVABILITY_ENABLED':'true'}
  config['services']['grafana'] = {'image':'grafana-pinned',
   'environment':{'GF_SERVER_SERVE_FROM_SUB_PATH':'true'}}
  config['services']['prometheus'] = {'image':'prometheus-pinned'}
  volumes['grafana_data'] = {'name':'aphrodize_grafana_data'}
  if candidate and mode == 'monitoring-disabled':
   config['services']['api']['environment'] = {}
  if candidate and mode == 'monitoring-removed':
   del config['services']['prometheus']
 print(json.dumps(config))
if 'run' in args and '--no-build' in args: sys.exit(64)
if 'ps' in args: print('container-'+args[-1])
if args[:1] == ['pull'] and mode == 'pull-fail': sys.exit(1)
if 'up' in args:
 count = int((state/'up-count').read_text()) if (state/'up-count').exists() else 0
 (state/'up-count').write_text(str(count+1))
 if mode in ('update-fail','rollback-fail') and (count == 0 or mode == 'rollback-fail'): sys.exit(1)
if 'exec' in args and mode == 'readiness-fail':
 if (state/'up-count').read_text() == '1': sys.exit(1)
if 'exec' in args and mode == 'monitoring-metrics-fail':
 if 'Check authenticated API telemetry' in sys.stdin.read():
  if (state/'up-count').read_text() == '1': sys.exit(1)
"""
FAKE_CURL = """#!/usr/bin/env python3
import os, sys
from pathlib import Path
state = Path(os.environ['FAKE_STATE'])
if os.environ.get('FAKE_MODE') == 'https-fail':
 if (state/'up-count').read_text() == '1': sys.exit(1)
if os.environ.get('FAKE_MODE') == 'monitoring-grafana-fail':
 if sys.argv[-1].endswith('/grafana/api/health') and (state/'up-count').read_text() == '1':
  sys.exit(1)
"""


class VmDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.deploy = self.root / "VM production"
        self.deploy.mkdir()
        (self.deploy / ".env").write_text("PRIVATE_SECRET=not-for-logs\n")
        (self.deploy / "compose.vm.yml").write_text("name: aphrodize\nservices: {}\n")
        (self.deploy / "docker").mkdir()
        (self.deploy / "docker/Caddyfile.vm").write_text("baseline TLS config")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, content in (("docker", FAKE_DOCKER), ("curl", FAKE_CURL)):
            path = self.bin / name
            path.write_text(content)
            path.chmod(0o755)
        self.state = self.root / "fake"
        self.state.mkdir()
        self.manifest = self.root / "manifest.json"
        self.data = {
            "schema_version": 1,
            "source_sha": "a" * 40,
            "run_id": 42,
            "site_url": "https://aphrodize.duckdns.org",
            "images": {
                service: f"ghcr.io/pacharaponk/aphrodize-{service}@sha256:{DIGEST}"
                for service in ("api", "frontend", "minio")
            },
        }
        self.manifest.write_text(json.dumps(self.data))
        self.env = {
            **os.environ,
            "PATH": str(self.bin) + ":" + os.environ["PATH"],
            "FAKE_STATE": str(self.state),
            "FAKE_DEPLOY_DIR": str(self.deploy),
        }

    def run_deploy(self, mode="", *extra):
        return subprocess.run(
            [
                "bash",
                str(ROOT / "scripts/deploy-vm.sh"),
                "--manifest",
                str(self.manifest),
                "--deploy-dir",
                str(self.deploy),
                *extra,
            ],
            env={**self.env, "FAKE_MODE": mode},
            text=True,
            capture_output=True,
            timeout=20,
        )

    def commands(self):
        file = self.state / "commands.jsonl"
        return [json.loads(line) for line in file.read_text().splitlines()] if file.exists() else []

    def test_success_captures_baseline_and_promotes_digest(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        release = self.deploy / ".releases"
        current = json.loads((release / "current-release.json").read_text())
        self.assertEqual(current["manifest"], self.data)
        previous = json.loads((release / "previous-release.json").read_text())
        config = json.loads(Path(previous["config"]).read_text())
        self.assertEqual(config["services"]["api"]["image"], "sha256:" + "a" * 64)
        candidate = json.loads(Path(current["config"]).read_text())
        self.assertEqual(candidate["services"]["api"]["image"], self.data["images"]["api"])
        self.assertEqual(
            candidate["services"]["api"]["volumes"][0]["source"],
            str(self.deploy / "storage/artifacts/uv"),
        )
        self.assertEqual(candidate["volumes"]["postgres_data"]["name"], "aphrodize_postgres_data")
        self.assertNotIn("not-for-logs", result.stdout + result.stderr)
        self.assertFalse(
            any("down" in command or "prune" in command for command in self.commands())
        )

    def test_preserves_extra_vm_volume_when_release_omits_optional_service(self):
        result = self.run_deploy("extra-vm-volume")
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads((self.deploy / ".releases/current-release.json").read_text())
        candidate = json.loads(Path(current["config"]).read_text())
        self.assertEqual(
            candidate["volumes"]["label_studio_data"],
            {"name": "aphrodize_label_studio_data"},
        )

    def test_monitoring_overlays_preserve_services_and_volumes_without_restarting_them(self):
        overlays = "compose.observability.yml,compose.observability-web.yml"
        for name in overlays.split(","):
            (self.deploy / name).write_text("services: {}\n")
        result = self.run_deploy("monitoring", "--overlays", overlays)
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads((self.deploy / ".releases/current-release.json").read_text())
        config = json.loads(Path(current["config"]).read_text())
        self.assertEqual(config["services"]["api"]["environment"]["OBSERVABILITY_ENABLED"], "true")
        self.assertIn("grafana", config["services"])
        self.assertIn("prometheus", config["services"])
        self.assertEqual(config["volumes"]["grafana_data"]["name"], "aphrodize_grafana_data")
        updates = [command for command in self.commands() if "up" in command]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0][-2:], ["api", "frontend"])

    def test_monitoring_removal_is_rejected_before_container_updates(self):
        for mode in ("monitoring-disabled", "monitoring-removed"):
            with self.subTest(mode=mode):
                result = self.run_deploy(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any("up" in c or "run" in c for c in self.commands()))
                self.assertFalse((self.deploy / ".releases/current-release.json").exists())

    def test_failed_metrics_or_grafana_check_rolls_back_monitoring_configuration(self):
        for mode in ("monitoring-metrics-fail", "monitoring-grafana-fail"):
            with self.subTest(mode=mode):
                (self.state / "up-count").unlink(missing_ok=True)
                result = self.run_deploy(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Rollback succeeded", result.stderr)
                current = json.loads((self.deploy / ".releases/current-release.json").read_text())
                config = json.loads(Path(current["config"]).read_text())
                self.assertIsNone(current["manifest"])
                self.assertIn("grafana", config["services"])
                self.assertEqual(
                    config["services"]["api"]["environment"]["OBSERVABILITY_ENABLED"], "true"
                )

    def test_volume_changes_rejected_with_safe_diagnostic_before_mutation(self):
        for mode in ("changed-volume", "new-volume"):
            with self.subTest(mode=mode):
                result = self.run_deploy(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Persistent volume configuration changed", result.stderr)
                self.assertNotIn("private-not-for-logs", result.stdout + result.stderr)
                self.assertFalse(any("up" in c or "run" in c for c in self.commands()))
                self.assertFalse((self.deploy / ".releases/current-release.json").exists())

    def test_pull_failure_does_not_update_services(self):
        result = self.run_deploy("pull-fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("up" in command or "run" in command for command in self.commands()))
        self.assertFalse((self.deploy / ".releases/current-release.json").exists())

    def test_invalid_manifest_and_overlay_rejected_before_docker(self):
        self.data["images"]["api"] = "evil:latest"
        self.manifest.write_text(json.dumps(self.data))
        self.assertNotEqual(self.run_deploy().returncode, 0)
        self.assertEqual(self.commands(), [])
        self.assertNotEqual(self.run_deploy("", "--overlays", "../../evil.yml").returncode, 0)

    def test_update_or_health_failure_restores_baseline(self):
        for mode in ("update-fail", "readiness-fail", "https-fail"):
            with self.subTest(mode=mode):
                counter = self.state / "up-count"
                counter.unlink(missing_ok=True)
                result = self.run_deploy(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Rollback succeeded", result.stderr)
                current = json.loads((self.deploy / ".releases/current-release.json").read_text())
                self.assertEqual(current["manifest"], None)
                self.assertEqual(counter.read_text(), "2")

    def test_failed_rollback_preserves_baseline_and_pending_state(self):
        result = self.run_deploy("rollback-fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Rollback failed", result.stderr)
        self.assertTrue((self.deploy / ".releases/pending-release.json").exists())
        current = json.loads((self.deploy / ".releases/current-release.json").read_text())
        self.assertEqual(current["manifest"], None)

    def test_unhealthy_baseline_prevents_mutation(self):
        result = self.run_deploy("baseline-unhealthy")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("up" in command or "pull" in command for command in self.commands()))

    def test_failed_deploy_can_be_recovered_then_retried(self):
        self.assertNotEqual(self.run_deploy("rollback-fail").returncode, 0)
        count = (self.state / "up-count").read_text()
        self.assertNotEqual(self.run_deploy().returncode, 0)
        self.assertEqual((self.state / "up-count").read_text(), count)
        result = subprocess.run(
            [
                "bash",
                str(ROOT / "scripts/deploy-vm.sh"),
                "--recover",
                "--deploy-dir",
                str(self.deploy),
            ],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.deploy / ".releases/pending-release.json").exists())
        self.assertEqual(self.run_deploy().returncode, 0)

    def test_failed_next_candidate_preserves_last_successful_rollback_pointer(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        previous_file = self.deploy / ".releases/previous-release.json"
        previous_before = json.loads(previous_file.read_text())
        current_before = json.loads((self.deploy / ".releases/current-release.json").read_text())
        (self.state / "up-count").unlink()
        self.data["source_sha"] = "c" * 40
        self.data["images"]["api"] = "ghcr.io/pacharaponk/aphrodize-api@sha256:" + "c" * 64
        self.manifest.write_text(json.dumps(self.data))
        result = self.run_deploy("update-fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(previous_file.read_text()), previous_before)
        self.assertEqual(
            json.loads((self.deploy / ".releases/current-release.json").read_text()), current_before
        )

    def test_manual_rollback_restores_previous_config(self):
        self.assertEqual(self.run_deploy().returncode, 0)
        result = subprocess.run(
            [
                "bash",
                str(ROOT / "scripts/deploy-vm.sh"),
                "--rollback",
                "--deploy-dir",
                str(self.deploy),
            ],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads((self.deploy / ".releases/current-release.json").read_text())
        self.assertIsNone(current["manifest"])

    def test_overlay_file_is_required_and_caddy_bind_is_preserved(self):
        self.assertNotEqual(self.run_deploy("", "--overlays", "compose.duckdns.yml").returncode, 0)
        self.assertFalse(any("up" in command for command in self.commands()))
        (self.deploy / "compose.duckdns.yml").write_text("services: {}\n")
        result = self.run_deploy("", "--overlays", "compose.duckdns.yml")
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads((self.deploy / ".releases/current-release.json").read_text())
        config = json.loads(Path(current["config"]).read_text())
        self.assertEqual(
            config["services"]["caddy"]["volumes"][0]["source"],
            str(self.deploy / "docker/Caddyfile.vm"),
        )

    def test_lock_contention_rejected(self):
        import fcntl

        self.deploy.joinpath(".releases").mkdir()
        with (self.deploy / ".releases/deploy.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertNotEqual(self.run_deploy().returncode, 0)
            self.assertEqual(self.commands(), [])


if __name__ == "__main__":
    unittest.main()
