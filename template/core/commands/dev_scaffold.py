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
    description = "Create a new reusable command module and a unittest without overwriting files"

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
        return {{"status": "ok", "dry_run": args.dry_run}}
'''
        test_code = f'''"""Smoke tests for {name}."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


class {classname}Tests(unittest.TestCase):
    def test_json_output(self):
        root = Path(__file__).resolve().parents[1]
        entry = "agent_cli.py" if (root / "agent_cli.py").exists() else "manage.py"
        result = subprocess.run(
            [sys.executable, str(root / entry), "{name}", "--dry-run", "--json"],
            cwd=root, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        self.assertEqual(json.loads(result.stdout)["result"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
'''
        source.parent.mkdir(parents=True, exist_ok=True)
        test.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(code, encoding="utf-8", errors="strict")
        test.write_text(test_code, encoding="utf-8", errors="strict")
        return {"status": "ok", "command": name, "files": [str(source), str(test)],
                "next": [f"dev-validate --file {source}", "system-docgen"]}
