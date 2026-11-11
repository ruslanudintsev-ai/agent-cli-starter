"""Structured error contract, sanitized failure handling and CLI compatibility."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "setup_starter_kit.py"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=35)


class StructuredErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        setup = run(self.root, str(INSTALLER), "--json")
        self.assertEqual(setup.returncode, 0, setup.stdout + setup.stderr)

    def add_command(self, name: str, behavior: str) -> None:
        module = self.root / "core/commands" / f"{name}.py"
        module.write_text(
            "import argparse\n"
            "from core.commands.base import BaseCommand, CommandError\n\n"
            f"class {name.title()}Command(BaseCommand):\n"
            f"    name = '{name}'\n"
            "    description = 'Test-only error contract probe'\n"
            "    def configure_parser(self, parser: argparse.ArgumentParser) -> None:\n"
            "        pass\n"
            "    def run(self, args: argparse.Namespace):\n"
            + "".join("        " + line + "\n" for line in behavior.splitlines()),
            encoding="utf-8",
        )

    def call(self, name: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = run(self.root, "manage.py", name, "--json")
        return result, json.loads(result.stdout)

    def test_known_command_error_is_structured_and_actionable(self) -> None:
        self.add_command("expected", '''
raise CommandError(
    "Target is missing.",
    error_code="MISSING_TARGET",
    suggested_fix="Use --target with a reviewed existing directory.",
    details={"field": "--target", "attempts": 1},
)
'''.strip())
        raw, data = self.call("expected")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["command"], "expected")
        result = data["result"]
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "MISSING_TARGET")
        self.assertEqual(result["message"], "Target is missing.")
        self.assertEqual(result["suggested_fix"], "Use --target with a reviewed existing directory.")
        self.assertEqual(result["details"], {"field": "--target", "attempts": 1})
        self.assertEqual(raw.stdout.count("\n"), 1)

    def test_unhandled_exception_does_not_expose_exception_message(self) -> None:
        self.add_command("unexpected", 'raise RuntimeError("SECRET_LOCAL_CREDENTIAL_XYZ")')
        raw, data = self.call("unexpected")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["result"]["error_code"], "UNEXPECTED_ERROR")
        self.assertEqual(data["result"]["error_type"], "RuntimeError")
        self.assertTrue(data["result"]["suggested_fix"])
        self.assertNotIn("SECRET_LOCAL_CREDENTIAL_XYZ", raw.stdout)

    def test_legacy_error_mapping_keeps_fields_and_adds_recovery_contract(self) -> None:
        self.add_command("legacy", "return {'status': 'error', 'errors': ['invalid example input']}")
        raw, data = self.call("legacy")
        self.assertEqual(raw.returncode, 1)
        result = data["result"]
        self.assertEqual(result["error_code"], "COMMAND_REPORTED_ERROR")
        self.assertEqual(result["errors"], ["invalid example input"])
        self.assertTrue(result["suggested_fix"])
        self.assertTrue(result["message"])

    def test_explicit_mapping_fields_are_preserved(self) -> None:
        self.add_command("explicit", '''
return {
    "status": "error",
    "error_code": "INVALID_SETTING",
    "message": "A setting is invalid.",
    "suggested_fix": "Review the documented setting.",
    "details": {"setting": "example"},
}
'''.strip())
        raw, data = self.call("explicit")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["result"]["error_code"], "INVALID_SETTING")
        self.assertEqual(data["result"]["suggested_fix"], "Review the documented setting.")
        self.assertEqual(data["result"]["details"]["setting"], "example")

    def test_success_result_is_unchanged(self) -> None:
        self.add_command("healthy", "return {'status': 'ok', 'items': 3}")
        raw, data = self.call("healthy")
        self.assertEqual(raw.returncode, 0)
        self.assertEqual(data["result"], {"status": "ok", "items": 3})

    def test_project_scan_has_specific_typed_error(self) -> None:
        result = run(self.root, "manage.py", "project-scan", "--root",
                     "path-that-does-not-exist", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        data = json.loads(result.stdout)["result"]
        self.assertEqual(data["error_code"], "INVALID_PROJECT_ROOT")
        self.assertIn("--root", data["suggested_fix"])

    def test_bad_error_code_and_wrong_run_type_fail_closed(self) -> None:
        self.add_command("badcode", 'raise CommandError("wrong", error_code="bad code")')
        raw, data = self.call("badcode")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["result"]["error_code"], "UNEXPECTED_ERROR")
        self.assertNotIn("bad code", raw.stdout)
        self.add_command("badreturn", "return 0")
        raw, data = self.call("badreturn")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["result"]["error_type"], "TypeError")
        self.assertEqual(data["result"]["error_code"], "UNEXPECTED_ERROR")

    def test_discovery_and_parser_warnings_do_not_leak_exception_messages(self) -> None:
        broken = self.root / "core/commands/broken_import.py"
        broken.write_text('raise RuntimeError("SECRET_FROM_IMPORT")\n', encoding="utf-8")
        parser_broken = self.root / "core/commands/broken_args.py"
        parser_broken.write_text(
            "from core.commands.base import BaseCommand\n"
            "class BrokenArgsCommand(BaseCommand):\n"
            "    name = 'broken-args'\n"
            "    description = 'test'\n"
            "    def configure_parser(self, parser):\n"
            "        raise RuntimeError('SECRET_FROM_PARSER')\n"
            "    def run(self, args):\n"
            "        return {'status': 'ok'}\n",
            encoding="utf-8",
        )
        raw = run(self.root, "manage.py", "sys-info", "--json")
        self.assertEqual(raw.returncode, 0, raw.stdout + raw.stderr)
        payload = json.loads(raw.stdout)
        self.assertTrue(any("broken_import" in item for item in payload["discovery_warnings"]))
        self.assertTrue(any("broken-args" in item for item in payload["discovery_warnings"]))
        self.assertNotIn("SECRET_FROM_IMPORT", raw.stdout + raw.stderr)
        self.assertNotIn("SECRET_FROM_PARSER", raw.stdout + raw.stderr)

    def test_error_details_remain_bounded(self) -> None:
        self.add_command("bounded", '''
raise CommandError(
    "Long message " + ("z" * 9000),
    error_code="BOUNDED_ERROR",
    suggested_fix="Inspect the approved error report.",
    details={"items": list(range(100))},
)
'''.strip())
        raw, data = self.call("bounded")
        self.assertEqual(raw.returncode, 1)
        self.assertEqual(data["result"]["error_code"], "BOUNDED_ERROR")
        self.assertLessEqual(len(data["result"]["details"]["items"]), 50)
        self.assertIn("_budget_notice", data)


if __name__ == "__main__":
    unittest.main()
