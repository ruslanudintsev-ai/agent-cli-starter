"""Opt-in snapshot and restore tests: truthful preview, conflicts, privacy and isolation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup_starter_kit.py"


def invoke(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", *args], cwd=root, text=True,
                          encoding="utf-8", errors="replace", capture_output=True,
                          timeout=35)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        result = invoke(self.root, str(INSTALLER), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def cli(self, *args: str, entry: str = "manage.py", root: Path | None = None) -> tuple[int, dict, str]:
        root = root or self.root
        result = invoke(root, entry, "config-snapshot", *args, "--json")
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout)["result"], result.stdout

    def test_list_does_not_create_storage(self) -> None:
        self.assertFalse((self.root / ".cle_state").exists())
        code, data, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(data["snapshots"], [])
        self.assertFalse((self.root / ".cle_state").exists())

    def test_create_preview_restore_and_undo_with_exact_bytes(self) -> None:
        target = self.root / "AGENTS.md"
        original = b"# Reviewed instructions\r\nOriginal value.\r\n"
        updated = b"# Different rules\r\nNew value.\r\n"
        target.write_bytes(original)
        code, snap, text = self.cli("--action", "create", "--file", "AGENTS.md")
        self.assertEqual(code, 0, text)
        sid = snap["snapshot_id"]
        self.assertTrue(sid.startswith("cfg-"))
        self.assertNotIn("Original value.", text)
        self.assertTrue((self.root / ".cle_state/checkpoints" / f"{sid}.json").exists())
        target.write_bytes(updated)
        code, preview, text = self.cli("--action", "restore", "--id", sid)
        self.assertEqual(code, 0, text)
        self.assertEqual(preview["restore_state"], "PREVIEW_ONLY")
        self.assertFalse(preview["applied"])
        self.assertTrue(preview["would_change"])
        self.assertEqual(target.read_bytes(), updated)
        self.assertNotIn("Different rules", text)

        code, restored, text = self.cli("--action", "restore", "--id", sid,
                                        "--apply", "--confirm", preview["confirmation_sha256"])
        self.assertEqual(code, 0, text)
        self.assertEqual(restored["restore_state"], "RESTORED")
        self.assertEqual(target.read_bytes(), original)
        undo = restored["undo_snapshot_id"]
        code, plan, _ = self.cli("--action", "restore", "--id", undo)
        self.assertEqual(code, 0)
        code, reverted, _ = self.cli("--action", "restore", "--id", undo,
                                       "--apply", "--confirm", plan["confirmation_sha256"])
        self.assertEqual(code, 0)
        self.assertTrue(reverted["applied"])
        self.assertEqual(target.read_bytes(), updated)

    def test_confirmation_missing_or_stale_is_not_success(self) -> None:
        target = self.root / "AGENTS.md"
        target.write_text("before", encoding="utf-8")
        _, snap, _ = self.cli("--action", "create", "--file", "AGENTS.md")
        sid = snap["snapshot_id"]
        target.write_text("changed", encoding="utf-8")
        _, preview, _ = self.cli("--action", "restore", "--id", sid)
        code, result, _ = self.cli("--action", "restore", "--id", sid, "--apply")
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "STALE_RESTORE_PLAN")
        target.write_text("changed AGAIN", encoding="utf-8")
        code, result, _ = self.cli("--action", "restore", "--id", sid, "--apply",
                                    "--confirm", preview["confirmation_sha256"])
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "STALE_RESTORE_PLAN")
        self.assertEqual(target.read_text(), "changed AGAIN")

    def test_only_explicit_guidance_paths_allowed(self) -> None:
        for bad in ("../AGENTS.md", ".env", "secrets.json", "src/settings.py",
                    ".agents/rules/../../AGENTS.md", "AGENTS.md/../CLAUDE.md",
                    ".cursor/rules/../../oops.md", "C:\\secret.env"):
            code, result, _ = self.cli("--action", "create", "--file", bad)
            self.assertEqual(code, 1, bad)
            self.assertEqual(result["error_code"], "INVALID_GUIDANCE_PATH")
        self.assertFalse((self.root / ".cle_state").exists())

    def test_missing_and_oversized_files_refused(self) -> None:
        (self.root / "AGENTS.md").unlink()
        code, result, _ = self.cli("--action", "create", "--file", "AGENTS.md")
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "GUIDANCE_FILE_MISSING")
        (self.root / "AGENTS.md").write_bytes(b"a" * (49 * 1024))
        code, result, _ = self.cli("--action", "create", "--file", "AGENTS.md")
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "GUIDANCE_FILE_TOO_LARGE")

    def test_symlink_ancestor_or_target_rejected_without_touching_outside(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / "private.md"
            secret.write_text("external data", encoding="utf-8")
            target = self.root / "AGENTS.md"
            target.unlink()
            try:
                target.symlink_to(secret)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable in this Windows environment.")
            code, result, raw = self.cli("--action", "create", "--file", "AGENTS.md")
            self.assertEqual(code, 1)
            self.assertEqual(result["error_code"], "UNSAFE_GUIDANCE_TARGET")
            self.assertEqual(secret.read_text(encoding="utf-8"), "external data")
            self.assertNotIn("external data", raw)

    def test_corrupt_snapshot_never_restores(self) -> None:
        target = self.root / "AGENTS.md"
        target.write_text("original", encoding="utf-8")
        _, snap, _ = self.cli("--action", "create", "--file", "AGENTS.md")
        storage = self.root / ".cle_state/checkpoints" / (snap["snapshot_id"] + ".json")
        record = json.loads(storage.read_text())
        record["payload"]["data_base64"] = "bm90IHRoZSBzYW1l"
        storage.write_text(json.dumps(record), encoding="utf-8")
        target.write_text("changed", encoding="utf-8")
        code, result, _ = self.cli("--action", "restore", "--id", snap["snapshot_id"], "--apply",
                                    "--confirm", "0" * 64)
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "SNAPSHOT_CORRUPT")
        self.assertEqual(target.read_text(), "changed")

    def test_missing_snapshots_and_no_change_are_not_false_restores(self) -> None:
        code, data, _ = self.cli("--action", "restore", "--id", "cfg-" + ("a" * 24))
        self.assertEqual(code, 1)
        self.assertEqual(data["error_code"], "SNAPSHOT_UNAVAILABLE")
        code, snap, _ = self.cli("--action", "create", "--file", "AGENTS.md")
        self.assertEqual(code, 0)
        code, preview, _ = self.cli("--action", "restore", "--id", snap["snapshot_id"])
        self.assertEqual(preview["would_change"], False)
        code, result, _ = self.cli("--action", "restore", "--id", snap["snapshot_id"], "--apply",
                                    "--confirm", preview["confirmation_sha256"])
        self.assertEqual(code, 1)
        self.assertEqual(result["error_code"], "NO_RESTORE_NEEDED")

    def test_isolated_runtime_uses_same_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "src").mkdir()
            (root / "manage.py").write_text("Django app, untouched", encoding="utf-8")
            r = invoke(root, str(INSTALLER), "--json")
            self.assertEqual(r.returncode, 0, r.stderr)
            entry = json.loads(r.stdout)["entrypoint"]
            self.assertEqual(entry, "tools/agent-cli-starter/manage.py")
            target = root / "AGENTS.md"
            original = target.read_bytes()
            code, snap, _ = self.cli("--action", "create", "--file", "AGENTS.md", entry=entry, root=root)
            self.assertEqual(code, 0)
            target.write_text("Changed", encoding="utf-8")
            code, preview, _ = self.cli("--action", "restore", "--id", snap["snapshot_id"], entry=entry, root=root)
            self.assertEqual(code, 0)
            code, restored, _ = self.cli("--action", "restore", "--id", snap["snapshot_id"],
                                           "--apply", "--confirm", preview["confirmation_sha256"],
                                           entry=entry, root=root)
            self.assertEqual(code, 0)
            self.assertTrue(restored["applied"])
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual((root / "manage.py").read_text(encoding="utf-8"), "Django app, untouched")


if __name__ == "__main__":
    unittest.main()
