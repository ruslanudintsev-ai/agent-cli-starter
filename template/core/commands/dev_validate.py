"""Static AST checks for standalone CLI plugins."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from core.commands.base import BaseCommand


class DevValidateCommand(BaseCommand):
    name = "dev-validate"
    description = "Validate Python command module using AST (no direct print, BaseCommand required)"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--file", required=True, help="Project-local Python command module")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        root = Path.cwd().resolve()
        path = Path(args.file).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return {"status": "error", "errors": ["Path must stay inside project root"]}
        if path.suffix != ".py" or not path.is_file():
            return {"status": "error", "errors": ["Not an existing Python file"]}
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            return {"status": "error", "errors": [f"Syntax/encoding error: {exc}"]}
        errors: list[str] = []
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        inheritors = [
            node for node in classes if any(
                (isinstance(base, ast.Name) and base.id == "BaseCommand")
                or (isinstance(base, ast.Attribute) and base.attr == "BaseCommand")
                for base in node.bases
            )
        ]
        if not inheritors:
            errors.append("No class inheriting BaseCommand")
        # An untouched generated scaffold is structurally parseable but not implemented.
        # This is a narrow diagnostic, NOT a proof that a marker-free module is correct.
        if any(isinstance(node, ast.Constant) and node.value == "NOT_IMPLEMENTED"
               for node in ast.walk(tree)):
            errors.append("Unimplemented scaffold: NOT_IMPLEMENTED marker remains")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                errors.append(f"Line {node.lineno}: direct print() is forbidden; return a mapping")
        for cls in inheritors:
            methods = {node.name for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for required in ("configure_parser", "run"):
                if required not in methods:
                    errors.append(f"{cls.name}: missing method {required}()")
        return {"status": "ok" if not errors else "error", "file": str(path.relative_to(root)),
                "valid": not errors, "classes": [item.name for item in inheritors],
                "scope": "Static structure only; behavior requires independent positive and negative acceptance tests",
                "behavior_verified": False, "errors": errors}
