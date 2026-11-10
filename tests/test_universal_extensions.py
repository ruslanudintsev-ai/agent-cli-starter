"""Tests for universal procedural learning, opt-in assertions and state safety."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import setup_starter_kit as starter

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("starter_checkpoint_state", REPO / "template/core/state.py")
assert SPEC and SPEC.loader
state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state)


def invoke(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=30)


class ExtensionTests(unittest.TestCase):
    def test_installs_manual_learning_and_patches_foreign_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "manage.py").write_text("# foreign owner\n", encoding="utf-8")
            outcome = invoke(str(REPO / "setup_starter_kit.py"), "--layout", "flat", cwd=root)
            self.assertEqual(outcome.returncode, 0, outcome.stderr)
            for relative in (
                ".agents/skills/self-improvement/SKILL.md",
                ".agents/rules/command-authoring.md",
                ".agents/skills/cli-tools/recipes.md",
                ".agents/backlog/cli-features.md",
                "core/state.py", "core/commands/checkpoints.py"
            ):
                self.assertTrue((root / relative).is_file(), relative)
            self.assertIn("python agent_cli.py", (root / ".agents/skills/cli-tools/recipes.md").read_text())
            self.assertIn("post_execution_assertions", (root / ".agents/rules/command-authoring.md").read_text())
            generated = (root / ".agents/skills/cli-tools/SKILL.md").read_text()
            self.assertIn("### `checkpoints`", generated)
            self.assertIn("--action", generated)
            self.assertNotIn("Proposal template", generated)

    def test_checkpoint_roundtrip_private_output_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = state.CheckpointStore(root)
            self.assertEqual(store.list_metadata(), [])
            store.save("build_stage_1", {"secret": "do-not-emit", "offset": 4}, ttl_seconds=100)
            self.assertEqual(store.load("build_stage_1"), {"secret": "do-not-emit", "offset": 4})
            self.assertTrue((root / ".cle_state/checkpoints/build_stage_1.json").is_file())
            self.assertNotIn("secret", str(store.list_metadata()))
            self.assertEqual(store.prune(), [])
            with mock.patch.object(state.time, "time", return_value=time.time() + 200):
                with self.assertRaisesRegex(state.CheckpointError, "expired"):
                    store.load("build_stage_1")
                self.assertEqual(store.prune(apply=False), ["build_stage_1"])
                self.assertTrue((root / ".cle_state/checkpoints/build_stage_1.json").exists())
                self.assertEqual(store.prune(apply=True), ["build_stage_1"])
            self.assertEqual(store.list_metadata(), [])

    def test_invalid_checkpoint_names_and_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = state.CheckpointStore(folder)
            for name in ("../private", "has.period", "9bad", "", "a" * 65):
                with self.assertRaises(state.CheckpointError):
                    store.save(name, {"ok": True})
            for value in (float("nan"), object()):
                with self.assertRaises(state.CheckpointError):
                    store.save("trial", {"invalid": value})
            with self.assertRaises(state.CheckpointError):
                store.save("too_big", {"data": "x" * 150000})
            with self.assertRaises(state.CheckpointError):
                store.save("bad_ttl", {}, ttl_seconds=0)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_cooperative_lock_and_corrupt_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = state.CheckpointStore(folder, lock_timeout=0.01)
            store.save("valid", {"ok": True})
            with store._exclusive():
                with self.assertRaisesRegex(state.CheckpointError, "locked"):
                    state.CheckpointStore(folder, lock_timeout=0.01).save("blocked", {"ok": True})
            (store.directory / "bad.json").write_text("{bad json", encoding="utf-8")
            self.assertIn("bad", [x["name"] for x in store.list_metadata() if not x["valid"]])
            self.assertEqual(store.prune(apply=True), [])  # Corrupt files are never removed automatically.
            self.assertTrue((store.directory / "bad.json").exists())

    def test_symlink_checkpoint_storage_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outer:
            root = Path(folder)
            outside = Path(outer)
            try:
                (root / ".cle_state").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaisesRegex(state.CheckpointError, "Symlink"):
                state.CheckpointStore(root).save("safe", {"ok": True})
            self.assertEqual(list(outside.iterdir()), [])

    def test_checkpoint_command_is_read_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            installed = invoke(str(REPO / "setup_starter_kit.py"), cwd=root)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            for argv in (("checkpoints", "--json"), ("checkpoints", "--action", "prune", "--json")):
                command = invoke("manage.py", *argv, cwd=root)
                self.assertEqual(command.returncode, 0, command.stderr)
                data = json.loads(command.stdout)["result"]
                self.assertEqual(data["status"], "ok")
            self.assertFalse((root / ".cle_state").exists())
            result = invoke("manage.py", "checkpoints", "--apply", "--json", cwd=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["result"]["status"], "error")

    def test_assertion_hook_warning_and_failure_are_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(REPO / "setup_starter_kit.py"), cwd=root).returncode, 0)
            module = root / "core/commands/health_demo.py"
            module.write_text('''import argparse
from core.commands.base import BaseCommand

class HealthDemoCommand(BaseCommand):
    name = "health-demo"
    description = "Test hook"
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--fail-check", action="store_true")
    def run(self, args: argparse.Namespace):
        return {"status": "ok", "operation": "unchanged"}
    def post_execution_assertions(self, args, data):
        if args.fail_check:
            raise RuntimeError("Do not expose this secret text")
        return [{"invariant": "test-read-only", "severity": "warning", "message": "Example"}]
''', encoding="utf-8")
            ok = invoke("manage.py", "health-demo", "--json", cwd=root)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            data = json.loads(ok.stdout)
            self.assertEqual(data["_system_health_warning"][0]["invariant"], "test-read-only")
            broken = invoke("manage.py", "health-demo", "--fail-check", "--json", cwd=root)
            self.assertEqual(broken.returncode, 0, broken.stdout + broken.stderr)
            failure = json.loads(broken.stdout)
            self.assertEqual(failure["result"]["status"], "ok")
            self.assertIn("_system_health_warning", failure)
            self.assertNotIn("Do not expose", broken.stdout)

    def test_force_upgrade_preserves_project_memories(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(REPO / "setup_starter_kit.py"), cwd=root).returncode, 0)
            original = {
                ".agents/skills/cli-tools/gotchas.md": "private, verified gotcha\n",
                ".agents/skills/cli-tools/recipes.md": "private, tested recipe\n",
                ".agents/backlog/cli-features.md": "private project backlog\n",
            }
            for filename, content in original.items():
                (root / filename).write_text(content, encoding="utf-8")
            result = invoke(str(REPO / "setup_starter_kit.py"), "--force", "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            for filename, content in original.items():
                self.assertEqual((root / filename).read_text(encoding="utf-8"), content)
                self.assertIn(filename, data["skipped"])
            self.assertIn("core/commands/base.py", data["overwritten"])

    def test_generated_skill_is_not_manual_memory_store(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(invoke(str(REPO / "setup_starter_kit.py"), cwd=root).returncode, 0)
            recipe = root / ".agents/skills/cli-tools/recipes.md"
            backlog = root / ".agents/backlog/cli-features.md"
            recipe.write_text("private, do-not-overwrite\n", encoding="utf-8")
            backlog.write_text("project-only proposal\n", encoding="utf-8")
            regen = invoke("manage.py", "system-docgen", "--json", cwd=root)
            self.assertEqual(regen.returncode, 0, regen.stderr)
            self.assertEqual(recipe.read_text(encoding="utf-8"), "private, do-not-overwrite\n")
            self.assertEqual(backlog.read_text(encoding="utf-8"), "project-only proposal\n")


if __name__ == "__main__":
    unittest.main()
