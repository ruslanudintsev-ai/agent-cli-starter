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
        source = Path("core/commands") / f"{module}.py"
        test = Path("tests") / f"test_{module}.py"
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
                 "message": "Scaffold only: implement the behavior and acceptance criteria"}}
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
        source.parent.mkdir(parents=True, exist_ok=True)
        test.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(code, encoding="utf-8", errors="strict")
        test.write_text(test_code, encoding="utf-8", errors="strict")
        return {"status": "ok", "command": name, "files": [str(source), str(test)],
                "feature_state": "SCAFFOLDED", "verification_state": "UNVERIFIED",
                "message": "Scaffold created; not functional and not accepted. Implement logic and both behavior tests.",
                "next": [f"dev-validate --file {source}",
                         f"python -m unittest tests.test_{module} -v", "system-docgen"]}
