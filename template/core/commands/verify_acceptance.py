"""Run independent, pinned behavioral acceptance cases for a trusted project CLI.

A signed policy or a sandbox is NOT provided: a reviewer must control the manifest
digest, fixtures and separate execution environment. No shell commands are accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from core.commands.base import BaseCommand

SHA_PATTERN = re.compile(r"[a-fA-F0-9]{64}\Z")
ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
FIELD_PATTERN = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){0,5}\Z")
SOURCE_PATTERN = re.compile(r"[a-z][a-z0-9_]*\.py\Z")
DISALLOWED_COMMANDS = frozenset(("verify-acceptance", "dev-scaffold", "system-docgen", "checkpoints"))
MAX_MANIFEST_BYTES = 65536
MAX_CASES = 20
MAX_CAPTURE_CHARS = 25000


class ContractFailure(ValueError):
    """Only generic failure codes; never echo potentially sensitive manifest content."""


def _fail(code: str) -> None:
    raise ContractFailure(code)


def _relative_file(root: Path, path: str) -> Path:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        _fail("unsafe_relative_path")
    raw = PurePosixPath(path)
    if raw.is_absolute() or any(part in ("", ".", "..") for part in raw.parts):
        _fail("unsafe_relative_path")
    target = root
    for segment in raw.parts:
        target = target / segment
        if target.is_symlink():
            _fail("symlink_rejected")
    if not target.is_file() or not target.resolve().is_relative_to(root):
        _fail("missing_or_external_file")
    return target


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _checked_json_object(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        _fail("invalid_manifest_json")
    if not isinstance(parsed, dict):
        _fail("manifest_must_be_object")
    return parsed


def _expect_name(value: Any) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        _fail("invalid_identifier")
    return value


def _validate_manifest(root: Path, value: dict[str, Any],
                       entrypoint: str) -> tuple[str, list[dict[str, Any]], dict[str, Path]]:
    if set(value) != {"schema_version", "task_id", "criteria_version", "command", "source", "fixtures", "cases"}:
        _fail("invalid_manifest_keys")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        _fail("unsupported_manifest_version")
    _expect_name(value["task_id"])
    _expect_name(value["criteria_version"])
    command = _expect_name(value["command"])
    if command in DISALLOWED_COMMANDS:
        _fail("disallowed_target_command")
    source = value["source"]
    expected_dir = (PurePosixPath(entrypoint).parent / "core" / "commands").as_posix()
    if (not isinstance(source, str)
            or PurePosixPath(source).parent.as_posix() != expected_dir
            or not SOURCE_PATTERN.fullmatch(PurePosixPath(source).name)):
        _fail("invalid_source_path")
    sources = {"source": _relative_file(root, source)}
    fixtures = value["fixtures"]
    if not isinstance(fixtures, dict) or len(fixtures) > 12:
        _fail("invalid_fixtures")
    for name, expected_hash in fixtures.items():
        _expect_name(name)
        if not isinstance(expected_hash, dict) or set(expected_hash) != {"path", "sha256"}:
            _fail("invalid_fixture_record")
        digest = expected_hash["sha256"]
        if not isinstance(digest, str) or not SHA_PATTERN.fullmatch(digest):
            _fail("invalid_fixture_hash")
        target = _relative_file(root, expected_hash["path"])
        if target.stat().st_size > 524288 or _digest(target.read_bytes()) != digest.lower():
            _fail("fixture_hash_mismatch")
        sources["fixture_" + name] = target
    cases = value["cases"]
    if not isinstance(cases, list) or not 2 <= len(cases) <= MAX_CASES:
        _fail("invalid_case_count")
    ids: set[str] = set()
    kinds: set[str] = set()
    argv_variants: set[tuple[str, ...]] = set()
    validated: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "kind", "argv", "expected_exit", "expected_result"}:
            _fail("invalid_case_keys")
        name = _expect_name(case["id"])
        if name in ids:
            _fail("duplicate_case_id")
        ids.add(name)
        kind = case["kind"]
        if kind not in ("positive", "negative"):
            _fail("invalid_case_kind")
        kinds.add(kind)
        argv = case["argv"]
        if (not isinstance(argv, list) or not 1 <= len(argv) <= 16
                or any(not isinstance(part, str) or not part or len(part) > 300
                       or any(ord(ch) < 32 for ch in part) for part in argv)):
            _fail("invalid_case_argv")
        if argv[0] != command or "--help" in argv or "-h" in argv or "--json" in argv:
            _fail("invalid_target_argv")
        if tuple(argv) in argv_variants:
            _fail("duplicate_test_input")
        argv_variants.add(tuple(argv))
        expected_exit = case["expected_exit"]
        if type(expected_exit) is not int or expected_exit not in (0, 1):
            _fail("invalid_exit_expectation")
        expected = case["expected_result"]
        if not isinstance(expected, dict) or not 2 <= len(expected) <= 12 or "status" not in expected:
            _fail("insufficient_behavior_expectations")
        if any(not isinstance(k, str) or not FIELD_PATTERN.fullmatch(k) for k in expected):
            _fail("invalid_expected_field")
        if any(type(v) not in (str, int, float, bool, type(None))
               or (isinstance(v, str) and len(v) > 300) for v in expected.values()):
            _fail("invalid_expected_value")
        validated.append(case)
    if kinds != {"positive", "negative"}:
        _fail("positive_and_negative_required")
    return command, validated, sources


def _observed_field(result: Mapping[str, Any], path: str) -> Any:
    current: Any = result
    for segment in path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return object()
        current = current[segment]
    return current


def _run_case(root: Path, entrypoint: str, case: dict[str, Any], timeout: int) -> dict[str, Any]:
    argv = [sys.executable, "-B", str(root / entrypoint), *case["argv"], "--json"]
    # Avoid forwarding credentials or arbitrary project environment variables.
    safe_environment = {key: os.environ[key] for key in (
        "PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "TMP", "TEMP", "TMPDIR",
        "LANG", "LC_ALL", "VIRTUAL_ENV",
    ) if key in os.environ}
    safe_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = {"id": case["id"], "kind": case["kind"], "passed": False}
    try:
        completed = subprocess.run(argv, cwd=root, env=safe_environment,
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {**result, "reason": "timeout"}
    except OSError:
        return {**result, "reason": "runner_unavailable"}
    if len(completed.stdout) > MAX_CAPTURE_CHARS or len(completed.stderr) > MAX_CAPTURE_CHARS:
        return {**result, "reason": "output_exceeds_budget"}
    if completed.returncode != case["expected_exit"]:
        return {**result, "reason": "exit_code_mismatch"}
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return {**result, "reason": "invalid_command_json"}
    if not isinstance(payload, dict) or payload.get("command") != case["argv"][0]:
        return {**result, "reason": "wrong_command_result"}
    returned = payload.get("result")
    if not isinstance(returned, dict):
        return {**result, "reason": "result_not_object"}
    for field, expected in case["expected_result"].items():
        observed = _observed_field(returned, field)
        if type(observed) is not type(expected) or observed != expected:
            return {**result, "reason": "behavior_mismatch", "field": field}
    return {**result, "passed": True, "reason": "matched"}


class VerifyAcceptanceCommand(BaseCommand):
    name = "verify-acceptance"
    description = "Run pinned positive/negative CLI acceptance oracles; fail closed without proof"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--manifest", required=True, help="Reviewed JSON manifest (can live outside project)")
        parser.add_argument("--sha256", required=True, help="Reviewer-pinned 64-character SHA-256 of manifest")
        parser.add_argument("--execute", action="store_true",
                            help="Explicitly authorize executing trusted destination CLI cases")
        parser.add_argument("--timeout", type=int, default=10, help="Per-case timeout in seconds (1–30)")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        root = Path.cwd().resolve()
        if not isinstance(args.sha256, str) or not SHA_PATTERN.fullmatch(args.sha256):
            return {"status": "error", "verification_state": "BLOCKED", "reason": "invalid_pinned_sha256"}
        if not 1 <= args.timeout <= 30:
            return {"status": "error", "verification_state": "BLOCKED", "reason": "invalid_timeout"}
        try:
            path = Path(args.manifest).expanduser()
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
                _fail("manifest_missing_or_oversize")
            raw = path.read_bytes()
            manifest_hash = _digest(raw)
            if manifest_hash != args.sha256.lower():
                _fail("manifest_hash_mismatch")
            manifest = _checked_json_object(raw)
            entrypoint = getattr(args, "_entrypoint", "manage.py")
            command, cases, checked_files = _validate_manifest(root, manifest, entrypoint)
            before = {key: _digest(file.read_bytes()) for key, file in checked_files.items()}
            before["manifest"] = _digest(path.read_bytes())
        except (ContractFailure, OSError, UnicodeError, TypeError) as exc:
            reason = str(exc) if isinstance(exc, ContractFailure) else "contract_unavailable"
            return {"status": "error", "verification_state": "BLOCKED", "reason": reason}
        proof = {
            "task_id": manifest["task_id"],
            "criteria_version": manifest["criteria_version"],
            "manifest_sha256": manifest_hash,
            "source_sha256": before["source"],
            "case_count": len(cases),
            "target_command": command,
        }
        if not args.execute:
            return {**proof, "status": "error", "verification_state": "UNVERIFIED",
                    "reason": "explicit_execution_required"}
        outcomes: list[dict[str, Any]] = []
        for case in cases:
            outcomes.append(_run_case(root, entrypoint, case, args.timeout))
        try:
            after = {key: _digest(file.read_bytes()) for key, file in checked_files.items()}
            after["manifest"] = _digest(path.read_bytes())
        except OSError:
            after = {}
        if before != after:
            return {**proof, "status": "error", "verification_state": "BLOCKED",
                    "reason": "source_or_fixture_changed_during_verification"}
        success = all(row["passed"] for row in outcomes)
        return {**proof, "status": "ok" if success else "error",
                "verification_state": "VERIFIED" if success else "FAILED",
                "passed_count": sum(row["passed"] for row in outcomes),
                "cases": outcomes}
