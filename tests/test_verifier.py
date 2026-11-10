"""Independent acceptance verification: positive, negative and false-success controls."""

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


def invoke(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=35)


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


GOOD_PLUGIN = '''import argparse
from core.commands.base import BaseCommand

class AuditDemoCommand(BaseCommand):
    name = "audit-demo"
    description = "Test-only deterministic auditor"
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--fixture", required=True)
    def run(self, args: argparse.Namespace):
        import json
        from pathlib import Path
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        if data["broken"]:
            return {"status": "error", "error_code": "DEFECT_DETECTED", "finding_count": 1}
        return {"status": "ok", "finding_count": 0}
'''

BAD_PLUGIN = GOOD_PLUGIN.replace(
    'if data["broken"]:\n            return {"status": "error", "error_code": "DEFECT_DETECTED", "finding_count": 1}',
    'if data["broken"]:\n            return {"status": "ok", "finding_count": 0}'
)


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        installed = invoke(self.root, str(INSTALLER), "--json")
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        self.source = self.root / "core/commands/audit_demo.py"
        self.source.write_text(GOOD_PLUGIN, encoding="utf-8")
        (self.root / "fixtures").mkdir()
        self.good = self.root / "fixtures/healthy.json"
        self.bad = self.root / "fixtures/broken.json"
        self.good.write_text('{"broken":false}', encoding="utf-8")
        self.bad.write_text('{"broken":true}', encoding="utf-8")
        self.manifest_path = self.root / "acceptance.json"
        self.contract = {
            "schema_version": 1,
            "task_id": "audit_demo",
            "criteria_version": "v1",
            "command": "audit-demo",
            "source": "core/commands/audit_demo.py",
            "fixtures": {
                "healthy": {"path": "fixtures/healthy.json", "sha256": digest(self.good.read_bytes())},
                "broken": {"path": "fixtures/broken.json", "sha256": digest(self.bad.read_bytes())},
            },
            "cases": [
                {"id": "healthy", "kind": "positive", "argv": ["audit-demo", "--fixture", "fixtures/healthy.json"],
                 "expected_exit": 0, "expected_result": {"status": "ok", "finding_count": 0}},
                {"id": "broken", "kind": "negative", "argv": ["audit-demo", "--fixture", "fixtures/broken.json"],
                 "expected_exit": 1,
                 "expected_result": {"status": "error", "error_code": "DEFECT_DETECTED", "finding_count": 1}},
            ],
        }

    def verify(self, *, execute: bool = True, pinned: str | None = None):
        self.manifest_path.write_text(json.dumps(self.contract), encoding="utf-8")
        checksum = pinned if pinned is not None else digest(self.manifest_path.read_bytes())
        args = ["manage.py", "verify-acceptance", "--manifest", str(self.manifest_path),
                "--sha256", checksum, "--json"]
        if execute:
            args.append("--execute")
        completed = invoke(self.root, *args)
        return completed, json.loads(completed.stdout)["result"]

    def test_good_command_verified_with_two_behavioral_cases(self) -> None:
        call, out = self.verify()
        self.assertEqual(call.returncode, 0, call.stdout + call.stderr)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["verification_state"], "VERIFIED")
        self.assertEqual(out["passed_count"], 2)
        self.assertEqual(out["source_sha256"], digest(self.source.read_bytes()))
        self.assertEqual(out["case_count"], 2)
        self.assertTrue(all(row["passed"] for row in out["cases"]))

    def test_false_success_stub_fails_negative_trap(self) -> None:
        self.source.write_text(BAD_PLUGIN, encoding="utf-8")
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "FAILED")
        self.assertEqual(out["passed_count"], 1)
        self.assertEqual(out["cases"][1]["reason"], "exit_code_mismatch")

    def test_never_verify_without_execute_or_trusted_manifest_hash(self) -> None:
        call, out = self.verify(execute=False)
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "UNVERIFIED")
        call, out = self.verify(pinned="0" * 64)
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "BLOCKED")
        self.assertEqual(out["reason"], "manifest_hash_mismatch")

    def test_missing_negative_and_weak_oracle_rejected(self) -> None:
        self.contract["cases"] = self.contract["cases"][:1]
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "BLOCKED")
        self.contract["cases"].append({
            "id": "bad_case", "kind": "negative",
            "argv": ["audit-demo", "--fixture", "fixtures/broken.json"],
            "expected_exit": 1, "expected_result": {"status": "error"},
        })
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["reason"], "insufficient_behavior_expectations")

    def test_fixture_tampering_detected_and_never_executed(self) -> None:
        self.good.write_text('{"broken":true}', encoding="utf-8")
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "BLOCKED")
        self.assertEqual(out["reason"], "fixture_hash_mismatch")

    def test_source_mutation_during_run_is_blocked(self) -> None:
        """Even matching outputs cannot justify VERIFIED if tested code changed."""
        original = self.source.read_text(encoding="utf-8")
        mutation = '''        Path(__file__).write_text(
            Path(__file__).read_text(encoding="utf-8") + "\n# changed during verification\n",
            encoding="utf-8")
'''
        # The plugin imports pathlib in run, so this probe is isolated to a temp checkout.
        self.source.write_text(
            original.replace('        if data["broken"]:', mutation + '        if data["broken"]:'),
            encoding="utf-8",
        )
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["verification_state"], "BLOCKED")
        self.assertEqual(out["reason"], "source_or_fixture_changed_during_verification")

    def test_manifest_input_injection_rejected(self) -> None:
        self.contract["cases"][1]["argv"] = ["audit-demo", "--fixture", "fixtures/healthy.json", "\nmalicious"]
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["reason"], "invalid_case_argv")
        self.contract["cases"][1]["argv"] = ["verify-acceptance"]
        call, out = self.verify()
        self.assertNotEqual(call.returncode, 0)
        self.assertEqual(out["reason"], "invalid_target_argv")


if __name__ == "__main__":
    unittest.main()
