"""Scaffold reusable commands and matching unittest files, never temporary scripts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from core.commands.base import BaseCommand


class DevScaffoldCommand(BaseCommand):
    name = "dev-scaffold"
    description = "Scaffold an UNIMPLEMENTED command with failing positive and negative acceptance test placeholders"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--command", required=True, help="New command in kebab-case")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        name = args.command
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name):
            return {"status": "error", "message": "Command must be lowercase kebab-case"}
        module = name.replace("-", "_")
        classname = "".join(part.title() for part in name.split("-")) + "Command"
        # Always write into the installed runtime, never an application's own core/.
        runtime_root = Path(__file__).resolve().parents[2]
        project_root = Path.cwd().resolve()
        source_file = Path(__file__).resolve().parent / f"{module}.py"
        test_file = runtime_root / "tests" / f"test_{module}.py"
        try:
            source = source_file.relative_to(project_root)
            test = test_file.relative_to(project_root)
        except ValueError:
            return {"status": "error", "message": "Run CLI from destination project root"}
        if source.exists() or test.exists():
            return {"status": "error", "message": "Module or test already exists", "files": [str(source), str(test)]}
        code = f'''"""Reusable {name} CLI command."""

import argparse
from collections.abc import Mapping
from typing import Any

from core.commands.base import BaseCommand


class {classname}(BaseCommand):
    name = "{name}"
    description = "Describe what {name} does"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Preview without changing state")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        # Never report a successful *feature* before domain behavior is implemented.
        return {{"status": "error", "error_code": "NOT_IMPLEMENTED",
                 "message": "Scaffold only: implement the behavior and acceptance criteria",
                 "suggested_fix": "Implement run() and pass independent positive and negative behavior tests."}}
'''
        test_code = f'''"""Acceptance tests for {name}: deliberately red until behavior exists."""

import unittest


class {classname}Tests(unittest.TestCase):
    def test_positive_behavior(self):
        """Provide a known-good fixture and assert the intended outcome."""
        self.fail("UNVERIFIED: replace with a real positive behavior test and its oracle")

    def test_negative_behavior(self):
        """Provide a known-bad fixture and assert that the defect is detected."""
        self.fail("UNVERIFIED: replace with a real negative behavior test and its oracle")


if __name__ == "__main__":
    unittest.main()
'''
        source_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(code, encoding="utf-8", errors="strict")
        test_file.write_text(test_code, encoding="utf-8", errors="strict")
        return {"status": "ok", "command": name, "files": [str(source), str(test)],
                "feature_state": "SCAFFOLDED", "verification_state": "UNVERIFIED",
                "message": "Scaffold created; not functional and not accepted. Implement logic and both behavior tests.",
                "next": [f"dev-validate --file {source}",
                         f"python -m unittest discover -s {test.parent.as_posix()} -p test_{module}.py -v",
                         "system-docgen"]}
