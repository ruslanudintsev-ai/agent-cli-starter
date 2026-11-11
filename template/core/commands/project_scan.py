"""Read-only, shallow project stack detection from common manifest markers.

This command never imports project code, runs programs, reads environment files,
recurses into source directories or emits the contents of any inspected manifest.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.commands.base import BaseCommand, CommandError

MAX_MANIFEST_BYTES = 64 * 1024
PYTHON_MARKERS = ("pyproject.toml", "requirements.txt", "Pipfile", "setup.cfg", "setup.py")
DOCKER_MARKERS = ("Dockerfile", "compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml")


def safe_marker(root: Path, filename: str) -> Path | None:
    """Only consider an ordinary file directly under the requested project root."""
    candidate = root / filename
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def bounded_manifest(path: Path) -> str:
    """Read bounded known manifests; reject large files rather than truncate."""
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


class ProjectScanCommand(BaseCommand):
    name = "project-scan"
    description = "Read-only stack detection and suggested project CLI commands"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--root", default=".", help="Existing project directory to inspect")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        root = Path(args.root).expanduser().resolve()
        if not root.is_dir():
            raise CommandError(
                "--root must identify an existing directory",
                error_code="INVALID_PROJECT_ROOT",
                suggested_fix="Choose an existing project directory and rerun project-scan --root <directory>.",
            )

        stacks: set[str] = set()
        proposed: set[str] = set()
        evidence: set[str] = set()
        notices: list[str] = []

        manifest = ""
        for filename in PYTHON_MARKERS:
            path = safe_marker(root, filename)
            if path is None:
                continue
            stacks.add("python")
            evidence.add(filename)
            if filename == "setup.py":  # Do not execute arbitrary Python from the target.
                continue
            try:
                if path.stat().st_size > MAX_MANIFEST_BYTES:
                    notices.append(f"Skipped oversized manifest: {filename}")
                else:
                    manifest += bounded_manifest(path).lower() + "\n"
            except OSError:
                notices.append(f"Could not read manifest: {filename}")
        if "python" in stacks:
            proposed.add("python-test")
        framework_matches = {
            "django": ("django", "django-check", "routes-list"),
            "flask": ("flask", "api-test", "routes-list"),
            "fastapi": ("fastapi", "api-test", "routes-list"),
            "playwright": ("playwright", "browser-test", "profile-audit"),
            "patchright": ("patchright", "browser-test", "profile-audit"),
            "pandas": ("data-science", "dataset-validate", None),
            "numpy": ("data-science", "dataset-validate", None),
        }
        for token, (stack, first, second) in framework_matches.items():
            if re.search(r"(?<![a-z0-9_-])" + re.escape(token) + r"(?![a-z0-9_-])", manifest):
                stacks.add(stack)
                proposed.add(first)
                if second:
                    proposed.add(second)

        package = safe_marker(root, "package.json")
        if package is not None:
            stacks.add("node")
            evidence.add("package.json")
            try:
                if package.stat().st_size > MAX_MANIFEST_BYTES:
                    notices.append("Skipped oversized manifest: package.json")
                else:
                    details = json.loads(bounded_manifest(package))
                    scripts = details.get("scripts", {}) if isinstance(details, dict) else {}
                    if isinstance(scripts, dict):
                        if "build" in scripts:
                            proposed.add("frontend-build")
                        if "test" in scripts:
                            proposed.add("frontend-test")
            except (OSError, ValueError, TypeError):
                notices.append("Could not inspect package.json scripts")

        for filename in DOCKER_MARKERS:
            if safe_marker(root, filename) is not None:
                evidence.add(filename)
                stacks.add("docker-compose" if "compose" in filename else "docker")
                if "compose" in filename:
                    proposed.add("services-status")

        # Metadata check only; never read a SQLite database or emit its filename.
        try:
            if any(p.is_file() and not p.is_symlink() and p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
                   for p in root.iterdir()):
                stacks.add("sqlite")
                proposed.add("db-inspect")
        except OSError:
            notices.append("Could not inspect top-level database markers")

        return {
            "status": "ok",
            "detected_stack": sorted(stacks),
            "evidence": sorted(evidence),
            "recommended_commands": sorted(proposed),
            "recommendations_installed": False,
            "scope": "shallow markers and bounded manifests only; no code or shell execution",
            "notices": notices,
        }
