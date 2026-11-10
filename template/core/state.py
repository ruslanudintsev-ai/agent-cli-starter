"""Project-local, opt-in, atomic JSON checkpoints for long-running commands.

No background jobs, automatic recovery, arbitrary code execution, or cloud sync.
The invoking command owns serialization, expiry policy and validation on resume.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import tempfile
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_MAX_BYTES = 128 * 1024


class CheckpointError(ValueError):
    """A checkpoint is unavailable, invalid, expired or unsafe to access."""


class CheckpointStore:
    """Small JSON checkpoint store under <project>/.cle_state/checkpoints.

    Existing symlinks at controlled paths are rejected. Files are written with
    os.replace while an exclusive per-store lock protects cooperating writers.
    A lock left after a hard crash is deliberately never deleted automatically.
    """

    def __init__(self, project_root: str | Path, *, lock_timeout: float = 2.0) -> None:
        self.root = Path(project_root).resolve()
        if not self.root.is_dir():
            raise CheckpointError("Project root must be an existing directory")
        self.directory = self.root / ".cle_state" / "checkpoints"
        self.lock_timeout = max(0.0, float(lock_timeout))

    def _check_directory(self, create: bool = False) -> bool:
        for part in (self.root / ".cle_state", self.directory):
            if part.is_symlink():
                raise CheckpointError("Symlink in checkpoint storage path is not allowed")
            if part.exists() and not part.is_dir():
                raise CheckpointError("Checkpoint storage path is not a directory")
            if create and not part.exists():
                part.mkdir(mode=0o700)
        return self.directory.is_dir()

    def _path(self, name: str) -> Path:
        if not isinstance(name, str) or _NAME.fullmatch(name) is None:
            raise CheckpointError("Name must be 1-64 alphanumeric, underscore or dash characters, starting with a letter")
        self._check_directory()
        path = self.directory / f"{name}.json"
        if path.is_symlink():
            raise CheckpointError("Symlink checkpoint entries are not allowed")
        return path

    @contextlib.contextmanager
    def _exclusive(self) -> Iterator[None]:
        self._check_directory(create=True)
        lock = self.directory / ".write.lock"
        deadline = time.monotonic() + self.lock_timeout
        while True:
            try:
                descriptor = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
                break
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise CheckpointError("Checkpoint store is locked; inspect the writer before removing its lock") from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.unlink(missing_ok=True)

    def save(self, name: str, payload: Mapping[str, Any], *, ttl_seconds: int = 86400) -> None:
        """Persist a bounded JSON mapping. The caller is responsible for data privacy."""
        if not isinstance(payload, Mapping):
            raise CheckpointError("Checkpoint payload must be a mapping")
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds <= 0:
            raise CheckpointError("ttl_seconds must be a positive integer")
        path = self._path(name)
        now = time.time()
        try:
            body = json.dumps({"version": 1, "created_at": now, "expires_at": now + ttl_seconds,
                               "payload": payload}, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise CheckpointError("Checkpoint payload must be JSON-serializable") from exc
        if len(body) > _MAX_BYTES:
            raise CheckpointError("Checkpoint exceeds 128 KiB")
        with self._exclusive():
            path = self._path(name)
            if path.exists() and not path.is_file():
                raise CheckpointError("Checkpoint target is not a file")
            fd, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=str(self.directory))
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(body)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def _read(self, name: str) -> dict[str, Any]:
        path = self._path(name)
        if not path.is_file():
            raise CheckpointError("Checkpoint not found")
        if path.stat().st_size > _MAX_BYTES:
            raise CheckpointError("Checkpoint is larger than 128 KiB")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, ValueError, OSError) as exc:
            raise CheckpointError("Corrupt or inaccessible checkpoint") from exc
        if (not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("payload"), dict)
                or not isinstance(data.get("expires_at"), (int, float))
                or isinstance(data.get("expires_at"), bool)
                or not math.isfinite(data["expires_at"])):
            raise CheckpointError("Invalid checkpoint schema")
        return data

    def load(self, name: str) -> dict[str, Any]:
        """Return unexpired JSON payload; never execute or unpickle checkpoint data."""
        data = self._read(name)
        if time.time() >= data["expires_at"]:
            raise CheckpointError("Checkpoint expired; start a new task or explicitly revalidate")
        return data["payload"]

    def list_metadata(self) -> list[dict[str, Any]]:
        """List checkpoint names and expiry only, NEVER stored payloads."""
        if not self._check_directory():
            return []
        entries: list[dict[str, Any]] = []
        for path in sorted(self.directory.glob("*.json")):
            if path.is_symlink() or not _NAME.fullmatch(path.stem):
                continue
            try:
                value = self._read(path.stem)
                expiry = value["expires_at"]
                entries.append({"name": path.stem, "expired": time.time() >= expiry,
                                "expires_at": expiry, "valid": True})
            except CheckpointError:
                entries.append({"name": path.stem, "valid": False})
        return entries

    def prune(self, *, apply: bool = False) -> list[str]:
        """Preview or explicitly delete only expired valid entries; never corrupt ones."""
        if not self._check_directory():
            return []
        if not apply:
            return [e["name"] for e in self.list_metadata() if e["valid"] and e.get("expired")]
        with self._exclusive():
            removed: list[str] = []
            for entry in self.list_metadata():
                if entry["valid"] and entry.get("expired"):
                    self._path(entry["name"]).unlink()
                    removed.append(entry["name"])
            return removed
