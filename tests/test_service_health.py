"""Read-only service-health behavior and negative acceptance scenarios."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup_starter_kit.py"


def call(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", *argv], cwd=root,
                          capture_output=True, encoding="utf-8", errors="replace",
                          text=True, timeout=40)


class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        r = call(self.root, str(INSTALLER), "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def health(self, *argv: str) -> tuple[int, dict]:
        r = call(self.root, "manage.py", "service-health", *argv, "--json")
        self.assertTrue(r.stdout.strip(), r.stderr)
        return r.returncode, json.loads(r.stdout)["result"]

    def test_full_check_is_healthy_and_docs_discover_command(self) -> None:
        code, result = self.health()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["health_state"], "HEALTHY")
        self.assertEqual(set(result["checks"]), {"python", "disk", "workspace", "commands"})
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(result["checks"]["commands"]["discovery_warning_count"], 0)
        self.assertIn("service-health",
                      (self.root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8"))

    def test_component_selection_is_explicit(self) -> None:
        code, result = self.health("--component", "python")
        self.assertEqual(code, 0)
        self.assertEqual(list(result["checks"]), ["python"])
        self.assertEqual(result["component"], "python")
        self.assertIn("3.10", result["checks"]["python"]["required"])

    def test_insufficient_disk_fails_instead_of_claiming_success(self) -> None:
        code, result = self.health("--component", "disk", "--min-free-mb", "1000000000")
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "HEALTH_CHECK_FAILED")
        self.assertEqual(result["health_state"], "DEGRADED")
        self.assertEqual(result["failed_checks"], ["disk"])
        self.assertTrue(result["suggested_fix"])
        self.assertEqual(result["checks"]["disk"]["minimum_mb"], 1000000000)

    def test_invalid_threshold_has_typed_recovery_error(self) -> None:
        code, result = self.health("--component", "disk", "--min-free-mb", "-1")
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "INVALID_DISK_THRESHOLD")
        self.assertTrue(result["suggested_fix"])

    def test_missing_guidance_fails_without_creating_files(self) -> None:
        skill = self.root / ".agents/skills/cli-tools/SKILL.md"
        skill.unlink()
        code, result = self.health("--component", "workspace", "--dry-run")
        self.assertEqual(code, 1)
        self.assertEqual(result["failed_checks"], ["workspace"])
        self.assertFalse(result["checks"]["workspace"]["guidance_present"][
            ".agents/skills/cli-tools/SKILL.md"])
        self.assertFalse(skill.exists())
        self.assertFalse((self.root / ".cle_state").exists())
        self.assertTrue(result["dry_run"])

    def test_broken_plugin_discovery_is_not_silently_successful(self) -> None:
        broken = self.root / "core/commands/broken_health.py"
        broken.write_text('raise RuntimeError("SECRET_FROM_BROKEN_PLUGIN")\n', encoding="utf-8")
        r = call(self.root, "manage.py", "service-health", "--component", "commands", "--json")
        self.assertEqual(r.returncode, 1)
        result = json.loads(r.stdout)["result"]
        self.assertEqual(result["failed_checks"], ["commands"])
        self.assertEqual(result["checks"]["commands"]["discovery_warning_count"], 1)
        self.assertNotIn("SECRET_FROM_BROKEN_PLUGIN", r.stdout + r.stderr)

    def test_isolated_django_layout_uses_same_health_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manage.py").write_text("# foreign Django manage.py\n", encoding="utf-8")
            (root / "src").mkdir()
            installation = call(root, str(INSTALLER), "--json")
            self.assertEqual(installation.returncode, 0, installation.stdout + installation.stderr)
            plan = json.loads(installation.stdout)
            entrypoint = plan["entrypoint"]
            self.assertEqual(entrypoint, "tools/agent-cli-starter/manage.py")
            result = call(root, entrypoint, "service-health", "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            health = json.loads(result.stdout)["result"]
            self.assertEqual(health["health_state"], "HEALTHY")
            self.assertEqual(health["checks"]["commands"]["status"], "ok")
            self.assertEqual((root / "manage.py").read_text(), "# foreign Django manage.py\n")


if __name__ == "__main__":
    unittest.main()
