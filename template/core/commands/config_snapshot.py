"""Opt-in, one-file agent-guidance snapshots using the existing checkpoint store.

Only specifically allowed project guidance paths are supported. No raw file content
appears in CLI output, and restoring requires a current-state confirmation digest.
This is not a general-purpose filesystem rollback or a security sandbox.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from core.commands.base import BaseCommand, CommandError
from core.state import CheckpointError, CheckpointStore

MAX_FILE_BYTES = 48 * 1024
TTL_SECONDS = 7 * 24 * 3600
SNAPSHOT_PREFIX = "cfg-"
SNAPSHOT_ID = re.compile(r"cfg-[0-9a-f]{24}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
RULE_NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}\.md\Z")
CURSOR_NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}\.mdc\Z")
EXACT_FILES = frozenset({"AGENTS.md", "CLAUDE.md", "AIDER_CONVENTIONS.md"})


def _error(code: str, message: str, fix: str) -> None:
    raise CommandError(message, error_code=code, suggested_fix=fix)


def _allowed_file(value: str) -> str:
    """Restrict snapshots to one explicitly named agent-instruction file."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        _error("INVALID_GUIDANCE_PATH", "Unsupported guidance file path.",
               "Use a documented project-root agent instruction file.")
    parts = PurePosixPath(value).parts
    if value in EXACT_FILES:
        return value
    if (len(parts) == 3 and parts[:2] == (".agents", "rules")
            and RULE_NAME.fullmatch(parts[2])):
        return value
    if (len(parts) == 3 and parts[:2] == (".cursor", "rules")
            and CURSOR_NAME.fullmatch(parts[2])):
        return value
    _error("INVALID_GUIDANCE_PATH", "Unsupported guidance file path.",
           "Only AGENTS.md, CLAUDE.md, AIDER_CONVENTIONS.md, .agents/rules/*.md "
           "or .cursor/rules/*.mdc are allowed.")


def _target(root: Path, relative: str) -> Path:
    """Reject links at every component, unusual file types and missing targets."""
    checked = _allowed_file(relative)
    path = root
    for component in PurePosixPath(checked).parts:
        path = path / component
        if path.is_symlink():
            _error("UNSAFE_GUIDANCE_TARGET", "Symlink target refused.",
                   "Use a regular project-local file, not a link.")
    try:
        info = path.lstat()
    except OSError:
        _error("GUIDANCE_FILE_MISSING", "Guidance file is not accessible.",
               "Choose an existing, regular project instruction file.")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _error("UNSAFE_GUIDANCE_TARGET", "Non-regular or linked file refused.",
               "Use an ordinary single-link project instruction file.")
    if info.st_size > MAX_FILE_BYTES:
        _error("GUIDANCE_FILE_TOO_LARGE", "Guidance file exceeds 48 KiB.",
               "Use a smaller, reviewed instruction file.")
    return path


def _read(root: Path, relative: str) -> tuple[Path, bytes]:
    path = _target(root, relative)
    try:
        content = path.read_bytes()
    except OSError:
        _error("GUIDANCE_UNREADABLE", "Guidance file cannot be read.",
               "Check local file permissions before retrying.")
    if len(content) > MAX_FILE_BYTES:
        _error("GUIDANCE_FILE_TOO_LARGE", "Guidance file exceeds 48 KiB.",
               "Choose a smaller instruction file.")
    return path, content


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _save(store: CheckpointStore, relative: str, content: bytes) -> str:
    payload = {
        "kind": "agent-guidance-snapshot-v1",
        "relative_path": relative,
        "sha256": _sha(content),
        "data_base64": base64.b64encode(content).decode("ascii"),
    }
    try:
        for _ in range(4):
            name = SNAPSHOT_PREFIX + secrets.token_hex(12)
            if not any(row["name"] == name for row in store.list_metadata()):
                store.save(name, payload, ttl_seconds=TTL_SECONDS)
                return name
    except CheckpointError:
        _error("SNAPSHOT_STORAGE_UNAVAILABLE", "Local snapshot storage is unavailable.",
               "Inspect the private checkpoint directory and local permissions.")
    _error("SNAPSHOT_ID_COLLISION", "Unable to allocate a unique snapshot identifier.",
           "Retry creation in a trusted project workspace.")


def _load(store: CheckpointStore, snapshot_id: str) -> tuple[str, bytes, str]:
    if not isinstance(snapshot_id, str) or not SNAPSHOT_ID.fullmatch(snapshot_id):
        _error("INVALID_SNAPSHOT_ID", "Invalid snapshot ID.",
               "Use the complete cfg- ID returned by the create action.")
    try:
        record = store.load(snapshot_id)
    except CheckpointError:
        _error("SNAPSHOT_UNAVAILABLE", "Snapshot is missing, expired or inaccessible.",
               "Check config-snapshot --action list; create a new snapshot if needed.")
    if not isinstance(record, dict) or set(record) != {
        "kind", "relative_path", "sha256", "data_base64",
    } or record.get("kind") != "agent-guidance-snapshot-v1":
        _error("SNAPSHOT_CORRUPT", "Snapshot schema is invalid.",
               "Do not restore this snapshot; create and review a new one.")
    relative = _allowed_file(record["relative_path"])
    expected = record["sha256"]
    encoded = record["data_base64"]
    if not isinstance(expected, str) or not DIGEST.fullmatch(expected) or not isinstance(encoded, str):
        _error("SNAPSHOT_CORRUPT", "Snapshot metadata is invalid.",
               "Do not restore this snapshot.")
    if len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
        _error("SNAPSHOT_CORRUPT", "Snapshot payload exceeds the size limit.",
               "Do not restore this snapshot.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        _error("SNAPSHOT_CORRUPT", "Snapshot bytes cannot be decoded.",
               "Do not restore this snapshot.")
    if len(content) > MAX_FILE_BYTES or _sha(content) != expected:
        _error("SNAPSHOT_CORRUPT", "Snapshot integrity check failed.",
               "Do not restore this snapshot.")
    return relative, content, expected


def _plan_digest(snapshot_id: str, relative: str, saved: str, current: str) -> str:
    fields = [snapshot_id, relative, saved, current]
    return _sha(json.dumps(fields, separators=(",", ":")).encode("utf-8"))


def _atomic_restore(root: Path, relative: str, original_sha: str, content: bytes) -> None:
    path = _target(root, relative)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        temporary_fd, temporary_name = tempfile.mkstemp(prefix=".agent-restore-", dir=str(path.parent))
        try:
            with os.fdopen(temporary_fd, "wb") as writer:
                writer.write(content)
                writer.flush()
                os.fsync(writer.fileno())
            os.chmod(temporary_name, mode)
            # Check immediately before replace. This is a cooperative staleness
            # check, not protection against a hostile concurrent writer.
            _, live = _read(root, relative)
            if _sha(live) != original_sha:
                _error("STALE_RESTORE_PLAN", "Guidance file changed before replacement.",
                       "Rerun the preview and review the new confirmation digest.")
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    except OSError:
        _error("RESTORE_WRITE_FAILED", "Unable to atomically restore the guidance file.",
               "Check local permissions; the project file should remain unchanged.")


class ConfigSnapshotCommand(BaseCommand):
    name = "config-snapshot"
    description = "Snapshot and preview one agent instruction file; restore with explicit confirmation"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--action", choices=("list", "create", "restore"), default="list")
        parser.add_argument("--file", help="One reviewed project-relative agent guidance file")
        parser.add_argument("--id", help="Snapshot identifier for preview/restore")
        parser.add_argument("--apply", action="store_true", help="Explicitly allow a file restore")
        parser.add_argument("--confirm", help="Exact SHA-256 from the current restore preview")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        root = Path.cwd().resolve()
        store = CheckpointStore(root)
        if args.action == "list":
            if args.file or args.id or args.apply or args.confirm:
                _error("INVALID_SNAPSHOT_ARGUMENTS", "List action accepts no other options.",
                       "Use --action create --file PATH or --action restore --id ID.")
            try:
                snapshots = [
                    {"id": item["name"], "valid": item["valid"],
                     "expired": item.get("expired", False)}
                    for item in store.list_metadata()
                    if SNAPSHOT_ID.fullmatch(item["name"])
                ]
            except CheckpointError:
                _error("SNAPSHOT_STORAGE_UNAVAILABLE", "Local snapshot metadata unavailable.",
                       "Inspect private checkpoint storage before retrying.")
            return {"status": "ok", "action": "list", "count": len(snapshots),
                    "snapshots": snapshots, "contents_exposed": False}

        if args.action == "create":
            if not args.file or args.id or args.apply or args.confirm:
                _error("INVALID_SNAPSHOT_ARGUMENTS", "Create requires --file only.",
                       "Use --action create --file AGENTS.md.")
            relative = _allowed_file(args.file)
            _, content = _read(root, relative)
            sid = _save(store, relative, content)
            return {"status": "ok", "action": "create", "snapshot_id": sid,
                    "file": relative, "sha256": _sha(content), "expires_in_days": 7,
                    "contents_exposed": False,
                    "storage": "local .cle_state/checkpoints; plain-text base64, gitignored"}

        if args.file or not args.id or (args.confirm and not args.apply):
            _error("INVALID_SNAPSHOT_ARGUMENTS", "Restore requires --id; --confirm requires --apply.",
                   "Run --action restore --id ID to preview before confirming.")
        relative, snapshot_content, saved_sha = _load(store, args.id)
        _, current_content = _read(root, relative)
        current_sha = _sha(current_content)
        changed = current_sha != saved_sha
        token = _plan_digest(args.id, relative, saved_sha, current_sha)
        result: dict[str, Any] = {
            "status": "ok", "action": "restore", "file": relative,
            "snapshot_id": args.id, "snapshot_sha256": saved_sha,
            "current_sha256": current_sha,
            "would_change": changed,
            "confirmation_sha256": token,
            "contents_exposed": False,
        }
        if not args.apply:
            return {**result, "restore_state": "PREVIEW_ONLY", "applied": False}
        if not changed:
            _error("NO_RESTORE_NEEDED", "Guidance file already matches snapshot.",
                   "No restore is necessary.")
        if args.confirm != token:
            _error("STALE_RESTORE_PLAN", "Missing or outdated restore confirmation digest.",
                   "Preview again and pass its current confirmation_sha256 with --apply.")
        # Preserve the exact pre-restore bytes for a deliberate, separate undo.
        undo_id = _save(store, relative, current_content)
        _atomic_restore(root, relative, current_sha, snapshot_content)
        return {**result, "restore_state": "RESTORED", "applied": True,
                "undo_snapshot_id": undo_id}
