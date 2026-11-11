"""Read-only, model-agnostic local CLI health checks.

This command inspects local metadata only. It does not import additional
application code, run shell probes, repair services or certify production health.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.commands.base import BaseCommand, CommandError

MIN_PYTHON = (3, 10)
REQUIRED_COMMANDS = frozenset(("service-health", "sys-info", "project-scan"))
REQUIRED_GUIDANCE = (
    "AGENTS.md",
    ".agents/rules/cli-standard.md",
    ".agents/skills/cli-tools/SKILL.md",
)


class ServiceHealthCommand(BaseCommand):
    name = "service-health"
    description = "Read-only Python, disk, project guidance and CLI registration checks"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--component",
                            choices=("all", "python", "disk", "workspace", "commands"),
                            default="all",
                            help="Choose one local health check or all (default)")
        parser.add_argument("--min-free-mb", type=int, default=256,
                            help="Minimum available disk space in MiB (default: 256)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Explicitly state metadata-only, no-repair operation")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        if not 0 <= args.min_free_mb <= 1_000_000_000:
            raise CommandError(
                "--min-free-mb must be between 0 and 1000000000",
                error_code="INVALID_DISK_THRESHOLD",
                suggested_fix="Choose a nonnegative disk threshold in MiB.",
            )

        root = Path.cwd().resolve()
        selected = ("python", "disk", "workspace", "commands") if args.component == "all" else (args.component,)
        checks: dict[str, dict[str, Any]] = {}

        if "python" in selected:
            supported = sys.version_info[:2] >= MIN_PYTHON
            checks["python"] = {
                "status": "ok" if supported else "failed",
                "version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "required": "3.10+",
            }

        if "disk" in selected:
            try:
                free_bytes = shutil.disk_usage(root).free
            except OSError:
                checks["disk"] = {"status": "failed", "reason": "disk_metadata_unavailable"}
            else:
                free_mb = free_bytes // (1024 * 1024)
                checks["disk"] = {
                    "status": "ok" if free_mb >= args.min_free_mb else "failed",
                    "available_mb": free_mb,
                    "minimum_mb": args.min_free_mb,
                }

        if "workspace" in selected:
            existing = {path: (root / path).is_file() for path in REQUIRED_GUIDANCE}
            checks["workspace"] = {
                "status": "ok" if all(existing.values()) else "failed",
                "guidance_present": existing,
                "scope": "Project-root metadata only; files not read",
            }

        if "commands" in selected:
            registered = getattr(args, "_subparsers", {})
            names = set(registered) if isinstance(registered, dict) else set()
            missing = sorted(REQUIRED_COMMANDS - names)
            discovery_warning_count = len(getattr(args, "_discovery_warnings", []))
            checks["commands"] = {
                "status": "ok" if not missing and not discovery_warning_count else "failed",
                "registered_count": len(names),
                "missing_required": missing,
                "discovery_warning_count": discovery_warning_count,
            }

        failures = sorted(name for name, record in checks.items() if record["status"] != "ok")
        response: dict[str, Any] = {
            "status": "error" if failures else "ok",
            "health_state": "DEGRADED" if failures else "HEALTHY",
            "component": args.component,
            "dry_run": bool(args.dry_run),
            "checks": checks,
            "failed_checks": failures,
            "scope": ("Local Python, disk and project/CLI metadata only. "
                      "No network or application process checks; not production-readiness proof."),
        }
        if failures:
            response.update({
                "error_code": "HEALTH_CHECK_FAILED",
                "message": "One or more selected local health checks failed.",
                "suggested_fix": (
                    "Inspect the failed_checks and checks fields, correct the observed issue, "
                    "then rerun the same read-only health check."
                ),
            })
        return response
