"""Integration tests for the offline installer and installed CLI (stdlib only)."""

from __future__ import annotations

import io
import json
import subprocess
import setup_starter_kit as starter
from unittest import mock
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup_starter_kit.py"


def invoke(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30,
    )


class InstallTests(unittest.TestCase):
    def test_install_and_json_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            installer = invoke(str(INSTALLER), "--json", cwd=root)
            self.assertEqual(installer.returncode, 0, installer.stderr)
            data = json.loads(installer.stdout)
            self.assertEqual(data["entrypoint"], "manage.py")
            self.assertFalse(data["docgen_dry_run"])
            self.assertTrue((root / ".agents/skills/cli-tools/SKILL.md").exists())
            for args in (("sys-info", "--json"), ("--json", "sys-info")):
                result = invoke("manage.py", *args, cwd=root)
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = json.loads(result.stdout)
                self.assertEqual(parsed["result"]["status"], "ok")
                self.assertIn("ram_total_mb", parsed["result"])
            doc = (root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("| Argument | Type | Required | Default | Description |", doc)
            self.assertIn("dev-scaffold", doc)
            rerun = invoke(str(INSTALLER), "--json", cwd=root)
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertTrue(json.loads(rerun.stdout)["docgen_dry_run"])
            self.assertEqual(doc, (root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8"))
            ignore = (root / ".gitignore").read_text(encoding="utf-8")
            for item in (".cle_state/", ".cle_cache/", "__pycache__/"):
                self.assertEqual(ignore.count(item), 1)

    def test_foreign_manage_py_preserved_and_rules_patched(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            existing = "# a Django manage.py\nprint('stay')\n"
            (root / "manage.py").write_text(existing, encoding="utf-8")
            result = invoke(str(INSTALLER), "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["entrypoint"], "agent_cli.py")
            self.assertEqual((root / "manage.py").read_text(encoding="utf-8"), existing)
            self.assertTrue((root / "agent_cli.py").exists())
            instructions = (root / ".agents/rules/cli-standard.md").read_text(encoding="utf-8")
            self.assertIn("python agent_cli.py", instructions)
            info = invoke("agent_cli.py", "sys-info", "--json", cwd=root)
            self.assertEqual(info.returncode, 0, info.stderr)

    def test_safe_discovery_and_static_validator(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            broken = root / "core/commands/broken_plugin.py"
            broken.write_text("raise RuntimeError('broken import')\n", encoding="utf-8")
            info = invoke("manage.py", "sys-info", "--json", cwd=root)
            self.assertEqual(info.returncode, 0, info.stderr)
            self.assertTrue(any("broken_plugin" in warning for warning in
                                json.loads(info.stdout)["discovery_warnings"]))
            bad = root / "core/commands/bad.py"
            bad.write_text("print('bad')\n", encoding="utf-8")
            validation = invoke("manage.py", "dev-validate", "--file", str(bad), "--json", cwd=root)
            self.assertNotEqual(validation.returncode, 0)
            self.assertTrue(json.loads(validation.stdout)["result"]["errors"])

    def test_scaffold_validation_and_auto_doc(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            generated = invoke("manage.py", "dev-scaffold", "--command", "hello-world", "--json", cwd=root)
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            record = json.loads(generated.stdout)["result"]
            self.assertEqual(record["feature_state"], "SCAFFOLDED")
            self.assertEqual(record["verification_state"], "UNVERIFIED")
            validated = invoke("manage.py", "dev-validate", "--file",
                               "core/commands/hello_world.py", "--json", cwd=root)
            self.assertNotEqual(validated.returncode, 0, validated.stdout + validated.stderr)
            self.assertIn("NOT_IMPLEMENTED", validated.stdout)
            docgen = invoke("manage.py", "system-docgen", "--json", cwd=root)
            self.assertEqual(docgen.returncode, 0, docgen.stdout + docgen.stderr)
            skill = (root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("hello-world", skill)
            run = invoke("manage.py", "hello-world", "--dry-run", "--json", cwd=root)
            self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)["result"]["error_code"], "NOT_IMPLEMENTED")
            tests = invoke("-m", "unittest", "discover", "-s", "tests", "-v", cwd=root)
            self.assertNotEqual(tests.returncode, 0, tests.stdout + tests.stderr)
            self.assertIn("test_positive_behavior", tests.stdout + tests.stderr)
            self.assertIn("test_negative_behavior", tests.stdout + tests.stderr)
            self.assertIn("UNVERIFIED", tests.stdout + tests.stderr)

    def test_project_scan_is_read_only_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            (root / "pyproject.toml").write_text('[project]\ndependencies = ["Django", "playwright"]\n', encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"scripts": {"build": "secret-command-value", "test": "private-script"}}), encoding="utf-8")
            (root / ".env").write_text("SECRET_TOKEN=never-publish-me\n", encoding="utf-8")
            scan = invoke("manage.py", "project-scan", "--json", cwd=root)
            self.assertEqual(scan.returncode, 0, scan.stdout + scan.stderr)
            data = json.loads(scan.stdout)["result"]
            self.assertEqual(data["status"], "ok")
            self.assertIn("django", data["detected_stack"])
            self.assertIn("node", data["detected_stack"])
            self.assertIn("frontend-build", data["recommended_commands"])
            self.assertFalse(data["recommendations_installed"])
            self.assertNotIn("never-publish-me", scan.stdout)
            self.assertNotIn("secret-command-value", scan.stdout)
            self.assertNotIn("private-script", scan.stdout)
            self.assertTrue((root / ".env").exists())

    def test_project_scan_missing_root_and_read_only_markers(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            missing = invoke("manage.py", "project-scan", "--root", "not-a-directory", "--json", cwd=root)
            self.assertNotEqual(missing.returncode, 0)
            self.assertEqual(json.loads(missing.stdout)["result"]["status"], "error")
            (root / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
            (root / "database.sqlite3").write_bytes(b"not-a-real-database")
            good = invoke("manage.py", "project-scan", "--json", cwd=root)
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            payload = json.loads(good.stdout)["result"]
            self.assertIn("sqlite", payload["detected_stack"])
            self.assertIn("docker", payload["detected_stack"])
            self.assertNotIn("database.sqlite3", good.stdout)

    def test_installed_onboarding_and_generated_skill(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "manage.py").write_text("# existing Django manage\n", encoding="utf-8")
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            onboarding = (root / ".agents/rules/agent-onboarding.md").read_text(encoding="utf-8")
            self.assertIn("python agent_cli.py project-scan --json", onboarding)
            skill = (root / ".agents/skills/cli-tools/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("### `project-scan`", skill)
            self.assertIn("--root", skill)

    def test_output_budget(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            module = root / "core/commands/large_payload.py"
            module.write_text('''import argparse
from core.commands.base import BaseCommand

class LargeCommand(BaseCommand):
    name = "large"
    description = "Large output"
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        pass
    def run(self, args: argparse.Namespace):
        return {"status": "ok", "items": list(range(100)), "text": "x" * 6000}
''', encoding="utf-8")
            result = invoke("manage.py", "large", "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["result"]["items"]), 50)
            self.assertLessEqual(len(payload["result"]["text"]), 5050)
            self.assertGreater(payload["_budget_notice"]["truncated_nodes"], 0)


    def test_preview_does_not_modify_project(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "existing.txt").write_text("leave me alone", encoding="utf-8")
            (root / ".gitignore").write_text("# user ignore\n", encoding="utf-8")
            result = invoke(str(INSTALLER), "--dry-run", "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["dry_run"])
            self.assertIn("manage.py", data["planned_created"])
            self.assertIn(".gitignore", data["planned_overwritten"])
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".gitignore", "existing.txt"])
            self.assertEqual((root / ".gitignore").read_text(encoding="utf-8"), "# user ignore\n")

    def test_preview_existing_install_and_force(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(INSTALLER), cwd=root).returncode, 0)
            old = (root / "core/commands/base.py").read_bytes()
            result = invoke(str(INSTALLER), "--force", "--dry-run", "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertIn("core/commands/base.py", plan["planned_overwritten"])
            self.assertEqual((root / "core/commands/base.py").read_bytes(), old)
            self.assertEqual(list(root.glob(".agent_cli_install_*")), [])

    def test_foreign_alternate_entrypoint_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manage = "# foreign Django manage.py\n"
            alternate = "# foreign agent_cli.py\n"
            (root / "manage.py").write_text(manage, encoding="utf-8")
            (root / "agent_cli.py").write_text(alternate, encoding="utf-8")
            result = invoke(str(INSTALLER), "--force", "--json", cwd=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / "manage.py").read_text(encoding="utf-8"), manage)
            self.assertEqual((root / "agent_cli.py").read_text(encoding="utf-8"), alternate)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["agent_cli.py", "manage.py"])

    def test_rollback_restores_existing_files_and_cleans_created_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "AGENTS.md").write_text("existing project instructions\n", encoding="utf-8")
            (root / ".gitignore").write_text("# project rules\n", encoding="utf-8")
            result = subprocess.CompletedProcess(args=[], returncode=3, stdout="", stderr="injected docgen failure")
            with mock.patch.object(starter.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(RuntimeError, "original files restored"):
                    starter.install(root, force=True)
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), "existing project instructions\n")
            self.assertEqual((root / ".gitignore").read_text(encoding="utf-8"), "# project rules\n")
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".gitignore", "AGENTS.md"])

    def test_symlink_destination_cannot_escape_project(self) -> None:
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outer:
            root = Path(folder)
            outside = Path(outer) / "ignore"
            outside.write_text("external data", encoding="utf-8")
            try:
                (root / ".gitignore").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is not supported by this environment")
            result = invoke(str(INSTALLER), "--force", cwd=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Symlink destination", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "external data")
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".gitignore"])

    def test_revision_validation_and_pinned_template_download(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            invalid = invoke(str(INSTALLER), "--ref", "v1.2", "--dry-run", cwd=root)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("40-character", invalid.stderr)
            self.assertEqual(list(root.iterdir()), [])
        revision = "a" * 40
        visited: list[str] = []

        def fake_urlopen(url: str, timeout: int) -> io.BytesIO:
            visited.append(url)
            return io.BytesIO(b"synthetic safe template")

        with mock.patch.object(starter.urllib.request, "urlopen", side_effect=fake_urlopen):
            files = starter.load_templates(revision)
        self.assertEqual(len(files), len(starter.TEMPLATE_FILES))
        self.assertEqual(len(visited), len(starter.TEMPLATE_FILES))
        self.assertTrue(all(f"/{revision}/template/" in url for url in visited))

    def test_rollback_if_write_fails_mid_install(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".gitignore").write_bytes(b"# previous\r\n")
            original_write = starter._atomic_write
            calls = 0

            def partial_failure(path: Path, content: bytes, mode: int | None = None) -> None:
                nonlocal calls
                calls += 1
                if calls == 5:
                    raise OSError("injected disk error")
                original_write(path, content, mode)

            with mock.patch.object(starter, "_atomic_write", side_effect=partial_failure):
                with self.assertRaisesRegex(RuntimeError, "original files restored"):
                    starter.install(root)
            self.assertEqual((root / ".gitignore").read_bytes(), b"# previous\r\n")
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".gitignore"])

    def test_gitignore_crlf_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".gitignore").write_bytes(b".venv/\r\nexisting/\r\n")
            result = invoke(str(INSTALLER), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = (root / ".gitignore").read_bytes()
            self.assertTrue(actual.startswith(b".venv/\r\nexisting/\r\n"))
            self.assertNotIn(b"\n.cle_state/\n", actual)
            self.assertIn(b".cle_state/\r\n", actual)

    def test_memory_contract_is_sanitized_and_evidence_based(self) -> None:
        rule = (REPO / "template/.agents/rules/self-learning.md").read_text(encoding="utf-8")
        gotchas = (REPO / "template/.agents/skills/cli-tools/gotchas.md").read_text(encoding="utf-8")
        protocol = (REPO / "docs/PROCEDURAL_MEMORY.md").read_text(encoding="utf-8")
        self.assertIn("Post-Task Audit", rule)
        self.assertIn("private destination", rule)
        self.assertIn("Validation", gotchas)
        self.assertIn("root cause", protocol.lower())
        self.assertIn("Never automatically synchronize", protocol)

if __name__ == "__main__":
    unittest.main()
