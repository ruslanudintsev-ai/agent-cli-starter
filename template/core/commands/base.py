"""Stable JSON command contract with bounded output and optional telemetry."""

from __future__ import annotations

import abc
import argparse
import contextlib
import io
import json
import re
import sys
import time
from collections.abc import Mapping
from typing import Any

try:  # Optional only; no third-party dependency is required.
    import psutil  # type: ignore[import-not-found]
except ImportError:
    psutil = None


class _BoundedWriter(io.TextIOBase):
    """Capture accidental plugin stdout without collecting unlimited data."""

    def __init__(self, limit: int = 1000) -> None:
        self.limit = limit
        self.parts: list[str] = []
        self.length = 0
        self.dropped = 0

    def write(self, value: str) -> int:
        remaining = max(0, self.limit - self.length)
        self.parts.append(value[:remaining]) if remaining else None
        self.length += min(len(value), remaining)
        self.dropped += len(value) - remaining
        return len(value)

    def getvalue(self) -> str:
        return "".join(self.parts)


class CommandError(Exception):
    """Expected, agent-actionable command failure with machine-readable fields.

    Only include sanitized, non-secret messages and details here; the dispatcher
    bounds their size but cannot determine what information is confidential.
    """

    _CODE = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")

    def __init__(self, message: str, *, error_code: str = "COMMAND_ERROR",
                 suggested_fix: str = "Review the command's inputs and retry.",
                 details: Mapping[str, Any] | None = None) -> None:
        if not isinstance(error_code, str) or not self._CODE.fullmatch(error_code):
            raise ValueError("error_code must be an uppercase stable identifier")
        if not isinstance(message, str) or not isinstance(suggested_fix, str):
            raise TypeError("message and suggested_fix must be strings")
        if details is not None and not isinstance(details, Mapping):
            raise TypeError("details must be a mapping")
        super().__init__(message)
        self.error_code = error_code
        self.suggested_fix = suggested_fix
        self.details = dict(details) if details is not None else None

    def to_dict(self) -> dict[str, Any]:
        """Preserve a stable envelope; only use details intentionally supplied."""
        result: dict[str, Any] = {
            "status": "error",
            "error_code": self.error_code,
            "message": str(self),
            "suggested_fix": self.suggested_fix,
        }
        if self.details is not None:
            result["details"] = self.details
        return result


class BaseCommand(abc.ABC):
    """All commands return a mapping; the dispatcher prints exactly one result."""

    name: str = ""
    description: str = ""
    MAX_ITEMS = 50
    MAX_STRING = 5000
    MAX_DEPTH = 12
    MAX_JSON_CHARS = 20000

    @abc.abstractmethod
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Declare argparse arguments, without performing side effects."""

    @abc.abstractmethod
    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        """Return JSON-compatible data; never print directly."""

    def _apply_output_budgets(self, data: Any) -> tuple[Any, int]:
        """Recursively limit list length, string length, keys, and nesting."""
        truncated = 0

        def visit(value: Any, depth: int) -> Any:
            nonlocal truncated
            if depth >= self.MAX_DEPTH:
                truncated += 1
                return "[maximum nesting depth exceeded]"
            if isinstance(value, str):
                if len(value) > self.MAX_STRING:
                    truncated += 1
                    return value[: self.MAX_STRING] + f"… [truncated {len(value) - self.MAX_STRING} chars]"
                return value
            if isinstance(value, Mapping):
                pairs = list(value.items())
                if len(pairs) > self.MAX_ITEMS:
                    truncated += 1
                return {
                    str(key)[: self.MAX_STRING]: visit(item, depth + 1)
                    for key, item in pairs[: self.MAX_ITEMS]
                }
            if isinstance(value, (list, tuple)):
                if len(value) > self.MAX_ITEMS:
                    truncated += 1
                return [visit(item, depth + 1) for item in value[: self.MAX_ITEMS]]
            if value is None or isinstance(value, (bool, int, float)):
                return value
            truncated += 1
            return visit(str(value), depth + 1)

        return visit(data, 0), truncated

    @staticmethod
    def _normalize_command_result(data: Mapping[str, Any]) -> Mapping[str, Any]:
        """Keep existing command error details while adding stable recovery fields."""
        if data.get("status") != "error":
            return data
        normalized: dict[str, Any] = {
            "status": "error",
            "error_code": data.get("error_code") or "COMMAND_REPORTED_ERROR",
            "message": data.get("message") or "The command reported an error.",
            "suggested_fix": data.get("suggested_fix") or (
                "Inspect the command's error details, fix the cause, and rerun the relevant check."
            ),
        }
        for key, value in data.items():
            if key not in normalized:
                normalized[key] = value
        return normalized

    @staticmethod
    def _memory_mb() -> float | None:
        if psutil is None:
            return None
        try:
            return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
        except (OSError, ValueError, AttributeError):
            return None

    def post_execution_assertions(self, args: argparse.Namespace,
                                  data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Optional, read-only project checks; disabled by default.

        Return small warning mappings with an invariant and a safe message.
        Never use this hook to mutate state or perform automated remediation.
        """
        return []

    def execute(self, args: argparse.Namespace) -> int:
        """Isolate stray stdout, report exceptions, and serialize one bounded response."""
        started = time.perf_counter()
        captured = _BoundedWriter()
        checks: list[Mapping[str, Any]] = []
        try:
            with contextlib.redirect_stdout(captured):
                data = self.run(args)
                if not isinstance(data, Mapping):
                    raise TypeError("Command.run() must return a mapping")
                data = self._normalize_command_result(data)
                try:
                    proposed_checks = self.post_execution_assertions(args, data)
                    if not isinstance(proposed_checks, list) or not all(isinstance(v, Mapping) for v in proposed_checks):
                        raise TypeError("post_execution_assertions must return a list of mappings")
                    checks = proposed_checks[:10]
                except Exception as check_error:
                    checks = [{"invariant": "optional-health-check", "severity": "warning",
                               "message": "Project check unavailable", "error_type": type(check_error).__name__}]
            status = str(data.get("status", "ok"))
            exit_code = 0 if status == "ok" else 1
            clean, count = self._apply_output_budgets(data)
        except CommandError as exc:
            # Expected errors carry an actionable, sanitized recovery contract.
            clean, count = self._apply_output_budgets(exc.to_dict())
            exit_code = 1
        except Exception as exc:
            # Unanticipated exception text may contain secrets, local paths, or tokens.
            # Return only a diagnostic *type*; detailed debugging stays in private logs.
            clean, count = self._apply_output_budgets({
                "status": "error",
                "error_code": "UNEXPECTED_ERROR",
                "message": "The command failed unexpectedly.",
                "suggested_fix": (
                    "Check the command implementation and run focused tests in a trusted environment."
                ),
                "error_type": type(exc).__name__,
            })
            exit_code = 1
        telemetry = {
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "process_rss_mb": self._memory_mb(),
        }
        result: dict[str, Any] = {"command": self.name, "result": clean, "_telemetry": telemetry}
        if checks:
            bounded_checks, extra_count = self._apply_output_budgets(checks)
            result["_system_health_warning"] = bounded_checks
            count += extra_count
        if count or captured.dropped or captured.length:
            result["_budget_notice"] = {
                "truncated_nodes": count,
                "suppressed_stdout_chars": captured.length + captured.dropped,
                "limits": {"items": self.MAX_ITEMS, "string": self.MAX_STRING},
            }
        warnings = getattr(args, "_discovery_warnings", [])
        if warnings:
            result["discovery_warnings"] = warnings[:10]
        rendered = json.dumps(result, ensure_ascii=False, default=str)
        if len(rendered) > self.MAX_JSON_CHARS:
            result = {
                "command": self.name,
                "result": {"status": "truncated", "preview": rendered[:10000]},
                "_telemetry": telemetry,
                "_budget_notice": {"total_json_chars": len(rendered), "max_json_chars": self.MAX_JSON_CHARS},
            }
            rendered = json.dumps(result, ensure_ascii=False)
        if getattr(args, "json", False):
            sys.stdout.write(rendered + "\n")
        else:
            sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return exit_code
