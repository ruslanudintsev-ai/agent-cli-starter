"""Universal installer safety tests for occupied application roots."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup_starter_kit.py"
ENTRY = "tools/agent-cli-starter/manage.py"


def invoke(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=40)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IsolatedLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()
        (self.root / "src/views.py").write_text("APP_SOURCE = True\n", encoding="utf-8")
        (self.root / "manage.py").write_text("# django project\nprint('django')\n", encoding="utf-8")
        (self.root / "core/commands").mkdir(parents=True)
        (self.root / "core/commands/base.py").write_text("# foreign core\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text(
            '[project]\ndependencies = ["Django"]\n', encoding="utf-8")

    def install(self, *args: str) -> dict:
        p = invoke(self.root, str(INSTALLER), *args, "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def test_auto_preview_and_apply_preserve_application_code(self) -> None:
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in (
            self.root / "manage.py", self.root / "core/commands/base.py",
            self.root / "src/views.py", self.root / "pyproject.toml"
        )}
        preview = self.install("--dry-run", "--integrate-agents")
        self.assertEqual(preview["layout"], "isolated")
        self.assertEqual(preview["installation_state"], "PLANNED")
        self.assertEqual(preview["agent_adoption_state"], "UNVERIFIED")
        self.assertEqual(preview["entrypoint"], ENTRY)
        self.assertIn("tools/agent-cli-starter/core/commands/base.py", preview["planned_created"])
        self.assertFalse((self.root / "tools").exists())
        applied = self.install("--integrate-agents")
        self.assertEqual(applied["installation_state"], "FILES_INSTALLED")
        self.assertEqual(applied["agent_adoption_state"], "UNVERIFIED")
        self.assertEqual(applied["next_verification_commands"][0],
                         f"python {ENTRY} sys-info --json")
        for rel, content in before.items():
            self.assertEqual((self.root / rel).read_bytes(), content)
        self.assertTrue((self.root / ENTRY).is_file())
        self.assertIn(f"python {ENTRY}", (self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn(f"python {ENTRY}",
                      (self.root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8"))
        for name in ("sys-info", "project-scan"):
            result = invoke(self.root, ENTRY, name, "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["result"]["status"], "ok")
        self.assertEqual(self.install()["layout"], "isolated")

    def test_namespace_scaffold_is_red_and_avoids_foreign_core_and_tests(self) -> None:
        self.install()
        original = (self.root / "core/commands/base.py").read_bytes()
        p = invoke(self.root, ENTRY, "dev-scaffold", "--command", "audit-demo", "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        value = json.loads(p.stdout)["result"]
        self.assertEqual(value["feature_state"], "SCAFFOLDED")
        module = "tools/agent-cli-starter/core/commands/audit_demo.py"
        tests = "tools/agent-cli-starter/tests/test_audit_demo.py"
        self.assertTrue((self.root / module).is_file())
        self.assertTrue((self.root / tests).is_file())
        self.assertFalse((self.root / "core/commands/audit_demo.py").exists())
        self.assertEqual((self.root / "core/commands/base.py").read_bytes(), original)
        syntax = invoke(self.root, ENTRY, "dev-validate", "--file", module, "--json")
        self.assertNotEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        self.assertIn("NOT_IMPLEMENTED", syntax.stdout)
        red = invoke(self.root, "-m", "unittest", "discover", "-s",
                     "tools/agent-cli-starter/tests", "-v")
        self.assertNotEqual(red.returncode, 0, red.stdout + red.stderr)
        self.assertIn("test_negative_behavior", red.stdout + red.stderr)
        doc = invoke(self.root, ENTRY, "system-docgen", "--json")
        self.assertEqual(doc.returncode, 0, doc.stdout + doc.stderr)
        skill = (self.root / ".agents/skills/cli-tools/SKILL.md").read_text()
        self.assertIn("audit-demo", skill)
        self.assertIn(f"python {ENTRY}", skill)

    def test_verifier_executes_isolated_entrypoint_not_django_manage(self) -> None:
        self.install()
        source = self.root / "tools/agent-cli-starter/core/commands/check_demo.py"
        source.write_text('''import argparse
from pathlib import Path
from core.commands.base import BaseCommand

class CheckDemoCommand(BaseCommand):
    name = "check-demo"
    description = "Positive and negative cases"
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--fixture", required=True)
    def run(self, args: argparse.Namespace):
        value = Path(args.fixture).read_text(encoding="utf-8").strip()
        if value == "bad":
            return {"status": "error", "error_code": "BAD_INPUT", "count": 1}
        return {"status": "ok", "count": 0}
''', encoding="utf-8")
        (self.root / "fixtures").mkdir()
        good = self.root / "fixtures/good.txt"
        bad = self.root / "fixtures/bad.txt"
        good.write_text("good", encoding="utf-8")
        bad.write_text("bad", encoding="utf-8")
        record = {
            "schema_version": 1, "task_id": "check_demo", "criteria_version": "v1",
            "command": "check-demo",
            "source": "tools/agent-cli-starter/core/commands/check_demo.py",
            "fixtures": {
                "good": {"path": "fixtures/good.txt", "sha256": checksum(good)},
                "bad": {"path": "fixtures/bad.txt", "sha256": checksum(bad)},
            },
            "cases": [
                {"id": "good", "kind": "positive",
                 "argv": ["check-demo", "--fixture", "fixtures/good.txt"], "expected_exit": 0,
                 "expected_result": {"status": "ok", "count": 0}},
                {"id": "bad", "kind": "negative",
                 "argv": ["check-demo", "--fixture", "fixtures/bad.txt"], "expected_exit": 1,
                 "expected_result": {"status": "error", "error_code": "BAD_INPUT", "count": 1}},
            ],
        }
        manifest = self.root / "acceptance.json"
        manifest.write_text(json.dumps(record), encoding="utf-8")
        result = invoke(self.root, ENTRY, "verify-acceptance", "--manifest",
                        "acceptance.json", "--sha256", checksum(manifest),
                        "--execute", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads(result.stdout)["result"]
        self.assertEqual(value["verification_state"], "VERIFIED")
        self.assertEqual(value["passed_count"], 2)

    def test_foreign_isolated_directory_is_not_overwritten_even_with_force(self) -> None:
        foreign = self.root / "tools/agent-cli-starter"
        foreign.mkdir(parents=True)
        (foreign / "README.md").write_text("unrelated tool\n", encoding="utf-8")
        original = (self.root / "manage.py").read_bytes()
        p = invoke(self.root, str(INSTALLER), "--force", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("occupied", p.stderr)
        self.assertEqual((foreign / "README.md").read_text(), "unrelated tool\n")
        self.assertEqual((self.root / "manage.py").read_bytes(), original)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_explicit_flat_rejects_foreign_core_even_with_force(self) -> None:
        before = (self.root / "core/commands/base.py").read_bytes()
        result = invoke(self.root, str(INSTALLER), "--layout", "flat", "--force", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Foreign core/", result.stderr)
        self.assertEqual((self.root / "core/commands/base.py").read_bytes(), before)
        self.assertFalse((self.root / "agent_cli.py").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_existing_agents_integration_uses_selected_isolated_entrypoint(self) -> None:
        previous = "# Existing application policy\nNo unapproved deploys.\n"
        (self.root / "AGENTS.md").write_text(previous, encoding="utf-8")
        plan = self.install("--integrate-agents", "--dry-run")
        self.assertEqual(plan["guidance_state"], "integration_planned")
        self.assertEqual((self.root / "AGENTS.md").read_text(), previous)
        self.install("--integrate-agents")
        current = (self.root / "AGENTS.md").read_text()
        self.assertTrue(current.startswith(previous))
        self.assertIn(f"python {ENTRY}", current)
        self.install("--integrate-agents")
        self.assertEqual((self.root / "AGENTS.md").read_text(), current)


if __name__ == "__main__":
    unittest.main()
