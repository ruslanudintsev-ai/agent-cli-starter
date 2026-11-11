#!/usr/bin/env python3
"""Transactional zero-dependency installer for agent-cli-starter.

No project files are changed during --dry-run. Real installations pre-fetch the
complete template, validate destination paths, snapshot files to be modified,
and roll back owned writes if any installation or docgen step fails.

An installer is not a security sandbox: use only reviewed upstream revisions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPO = "ruslanudintsev-ai/agent-cli-starter"
TEMPLATE_FILES = (
    ".agents/rules/cli-standard.md",
    ".agents/rules/self-learning.md",
    ".agents/rules/agent-onboarding.md",
    ".agents/rules/command-authoring.md",
    ".agents/skills/cli-tools/SKILL.md",
    ".agents/skills/cli-tools/gotchas.md",
    ".agents/skills/cli-tools/recipes.md",
    ".agents/skills/self-improvement/SKILL.md",
    ".agents/backlog/cli-features.md",
    ".cursor/rules/agent-cli.mdc",
    "AGENTS.md",
    "CLAUDE.md",
    "AIDER_CONVENTIONS.md",
    "core/__init__.py",
    "core/state.py",
    "core/commands/__init__.py",
    "core/commands/base.py",
    "core/commands/sys_info.py",
    "core/commands/service_health.py",
    "core/commands/system_docgen.py",
    "core/commands/dev_scaffold.py",
    "core/commands/project_scan.py",
    "core/commands/checkpoints.py",
    "core/commands/config_snapshot.py",
    "core/commands/dev_validate.py",
    "core/commands/verify_acceptance.py",
    "manage.py",
)
IGNORE_LINES = (".cle_state/", ".cle_cache/", "__pycache__/")
ISOLATED_PREFIX = "tools/agent-cli-starter"
VALID_LAYOUTS = ("auto", "flat", "isolated")
# User-earned operational knowledge is never overwritten, even with --force.
PRESERVE_USER_NOTES = frozenset((
    ".agents/skills/cli-tools/gotchas.md",
    ".agents/skills/cli-tools/recipes.md",
    ".agents/backlog/cli-features.md",
))
MARKER = "# AGENT_CLI_STARTER_ENTRYPOINT"
PIN_RE = re.compile(r"[a-fA-F0-9]{40}\Z")
AGENTS_START = "<!-- agent-cli-starter:begin -->"
AGENTS_END = "<!-- agent-cli-starter:end -->"


@dataclass(frozen=True)
class Change:
    """One planned content change to a file under the selected project root."""

    relative: str
    destination: Path
    content: bytes
    existed: bool


def checked_revision(value: str) -> str:
    if value != "main" and not PIN_RE.fullmatch(value):
        raise ValueError("--ref must be 'main' or a complete 40-character Git commit SHA")
    return value.lower() if value != "main" else value


def _is_ours(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    return MARKER in path.read_text(encoding="utf-8", errors="replace")


def select_entrypoint(target: Path) -> str:
    """Protect any foreign manage.py AND agent_cli.py, even with --force."""
    existing_manage = target / "manage.py"
    if not existing_manage.exists() and not existing_manage.is_symlink():
        return "manage.py"
    if _is_ours(existing_manage):
        return "manage.py"
    alternate = target / "agent_cli.py"
    if alternate.exists() or alternate.is_symlink():
        if not _is_ours(alternate):
            raise ValueError("Both manage.py and agent_cli.py are occupied; refusing to overwrite either")
    return "agent_cli.py"


def choose_layout(target: Path, requested: str) -> str:
    """Preserve existing installs and isolate occupied project roots."""
    if requested not in VALID_LAYOUTS:
        raise ValueError("Invalid layout")
    if requested != "auto":
        return requested
    if _is_ours(target / "manage.py") or _is_ours(target / "agent_cli.py"):
        return "flat"
    if _is_ours(target / ISOLATED_PREFIX / "manage.py"):
        return "isolated"
    if any((target / marker).exists() for marker in
           ("manage.py", "agent_cli.py", "core", "src", "app", "pyproject.toml", "package.json")):
        return "isolated"
    return "flat"


def isolated_entrypoint(target: Path) -> str:
    """Refuse to merge with a foreign tools/agent-cli-starter tree."""
    directory = target / ISOLATED_PREFIX
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError("Isolated CLI destination is not a safe directory")
    if directory.exists() and any(directory.iterdir()) and not _is_ours(directory / "manage.py"):
        raise ValueError("Isolated CLI destination occupied by unrelated files")
    return f"{ISOLATED_PREFIX}/manage.py"


def load_templates(revision: str) -> dict[str, str]:
    """Load local source only when unpinned; pinned installs fetch that revision."""
    local = Path(__file__).resolve().parent / "template" if "__file__" in globals() else None
    source: dict[str, str] = {}
    for relative in TEMPLATE_FILES:
        candidate = local / relative if local is not None else None
        if revision == "main" and candidate is not None and candidate.is_file():
            source[relative] = candidate.read_text(encoding="utf-8")
        else:
            url = f"https://raw.githubusercontent.com/{REPO}/{revision}/template/{relative}"
            with urllib.request.urlopen(url, timeout=25) as response:
                source[relative] = response.read().decode("utf-8")
    return source


def checked_path(root: Path, relative: str) -> Path:
    """Reject traversal, links in destination components, and directory collisions."""
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"Unsafe target file: {relative}")
    target = root.joinpath(*parts)
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Symlink destination not allowed: {relative}")
        if cursor != target and cursor.exists() and not cursor.is_dir():
            raise ValueError(f"Non-directory path component in: {relative}")
    if target.exists() and not target.is_file():
        raise ValueError(f"File target is not a regular file: {relative}")
    return target


def gitignore_content(path: Path) -> tuple[bytes | None, list[str]]:
    # Preserve an existing file's line endings and all original bytes.
    raw = path.read_bytes() if path.exists() else b""
    current = raw.decode("utf-8")
    existing = {line.strip() for line in current.splitlines()}
    missing = [line for line in IGNORE_LINES if line not in existing]
    if not missing:
        return None, []
    newline = "\r\n" if b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"") else "\n"
    suffix = newline if current and not current.endswith(("\n", "\r")) else ""
    return (current + suffix + newline.join(missing) + newline).encode("utf-8"), missing


def make_plan(target: Path, *, force: bool, revision: str,
              integrate_agents: bool = False,
              layout: str = "auto") -> tuple[dict[str, object], list[Change], list[Change]]:
    """Build an inspection-ready action plan without changing the target."""
    target = target.expanduser().resolve()
    if not target.is_dir() or target == Path(target.anchor):
        raise ValueError("--target must be an existing project directory, not filesystem root")
    revision = checked_revision(revision)
    selected_layout = choose_layout(target, layout)
    # Never import an application's unrelated core/ during installer doc generation.
    if (selected_layout == "flat" and (target / "core").exists()
            and not (_is_ours(target / "manage.py") or _is_ours(target / "agent_cli.py"))):
        raise ValueError("Foreign core/ occupies flat runtime; choose --layout isolated")
    entrypoint = (select_entrypoint(target) if selected_layout == "flat"
                  else isolated_entrypoint(target))
    commands_dir = ("core/commands" if selected_layout == "flat"
                    else f"{ISOLATED_PREFIX}/core/commands")
    tests_dir = ("tests" if selected_layout == "flat"
                 else f"{ISOLATED_PREFIX}/tests")
    templates = load_templates(revision)  # complete all network reads before writing
    writes: list[Change] = []
    skipped: list[str] = []
    guidance_state = "new_file"
    for relative, content in templates.items():
        if relative == "manage.py":
            filename = entrypoint
        elif selected_layout == "isolated" and relative.startswith("core/"):
            filename = f"{ISOLATED_PREFIX}/{relative}"
        else:
            filename = relative
        destination = checked_path(target, filename)
        if filename == "AGENTS.md" and destination.exists():
            # Existing project policies are never replaced, even with --force.
            if integrate_agents:
                content_bytes = integrate_existing_agents(destination, entrypoint)
                if content_bytes is None:
                    skipped.append(filename)
                    guidance_state = "already_integrated"
                else:
                    writes.append(Change(filename, destination, content_bytes, True))
                    guidance_state = "integration_planned"
            else:
                skipped.append(filename)
                guidance_state = "existing_preserved"
            continue
        if destination.exists() and (not force or filename in PRESERVE_USER_NOTES):
            skipped.append(filename)
            continue
        rendered = (content.replace("__ENTRYPOINT__", entrypoint)
                    .replace("__COMMANDS_DIR__", commands_dir)
                    .replace("__TESTS_DIR__", tests_dir))
        writes.append(Change(filename, destination, rendered.encode("utf-8"), destination.exists()))
    gi = checked_path(target, ".gitignore")
    updated_ignore, added = gitignore_content(gi)
    extra = [Change(".gitignore", gi, updated_ignore, gi.exists())] if updated_ignore is not None else []
    plan: dict[str, object] = {
        "status": "ok",
        "source_revision": revision,
        "entrypoint": entrypoint,
        "layout": selected_layout,
        "commands_dir": commands_dir,
        "tests_dir": tests_dir,
        "planned_created": [c.relative for c in writes + extra if not c.existed],
        "planned_overwritten": [c.relative for c in writes + extra if c.existed],
        "skipped": skipped,
        "gitignore_additions": added,
        "docgen_dry_run": ".agents/skills/cli-tools/SKILL.md" in skipped,
        "guidance_state": guidance_state,
        "codex_override_present": (target / "AGENTS.override.md").exists(),
        "agent_adoption_state": "UNVERIFIED",
        "next_verification_commands": [
            f"python {entrypoint} sys-info --json",
            f"python {entrypoint} project-scan --json",
        ],
    }
    return plan, writes, extra



def integrate_existing_agents(path: Path, entrypoint: str) -> bytes | None:
    """Append a small managed reference without replacing project instructions."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    starts, ends = text.count(AGENTS_START), text.count(AGENTS_END)
    if starts != ends or starts > 1:
        raise ValueError("AGENTS.md contains incomplete/duplicate integration markers")
    if starts:
        if text.index(AGENTS_START) > text.index(AGENTS_END):
            raise ValueError("AGENTS.md integration markers are out of order")
        return None
    newline = "\r\n" if b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"") else "\n"
    block = (
        f"{AGENTS_START}\n"
        "## Agent CLI Starter (project-local)\n"
        f"Run reusable operations with `python {entrypoint} <command> --json`. "
        "First inspect `.agents/skills/cli-tools/SKILL.md` and "
        "`.agents/rules/cli-standard.md`; follow `.agents/rules/self-learning.md` "
        "and the project acceptance criteria before claiming VERIFIED. "
        "Project-specific instructions above remain authoritative.\n"
        f"{AGENTS_END}\n"
    ).replace("\n", newline)
    separator = (newline if text and not text.endswith(("\r", "\n")) else "") + (newline if text else "")
    return (text + separator + block).encode("utf-8")

def _atomic_write(path: Path, content: bytes, mode: int | None = None) -> None:
    """Replace an individual file atomically on its own filesystem."""
    fd, temp_name = tempfile.mkstemp(prefix=".agent_cli_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _ensure_dirs(parent: Path, root: Path, created_dirs: list[Path]) -> None:
    pending: list[Path] = []
    cursor = parent
    while cursor != root and not cursor.exists():
        pending.append(cursor)
        cursor = cursor.parent
    for directory in reversed(pending):
        directory.mkdir()
        created_dirs.append(directory)


def _restore(journal: list[tuple[Path, Path | None, int | None]], created_dirs: list[Path]) -> list[str]:
    failures: list[str] = []
    for path, backup, mode in reversed(journal):
        try:
            if backup is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_write(path, backup.read_bytes(), mode)
        except OSError as exc:
            failures.append(f"{path.name}: {type(exc).__name__}")
    for directory in reversed(created_dirs):
        try:
            directory.rmdir()
        except OSError:
            pass  # An unexpected file might have appeared; never delete it blindly.
    return failures


def install(target: Path, force: bool = False, dry_run: bool = False,
            revision: str = "main", integrate_agents: bool = False,
            layout: str = "auto") -> dict[str, object]:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required")
    root = target.expanduser().resolve()
    plan, writes, extra = make_plan(root, force=force, revision=revision,
                                   integrate_agents=integrate_agents, layout=layout)
    if dry_run:
        return {**plan, "installation_state": "PLANNED", "dry_run": True,
                "created": [], "overwritten": [], "gitignore_updated": False}

    changes = writes + extra
    created_dirs: list[Path] = []
    journal: list[tuple[Path, Path | None, int | None]] = []
    # Stage backups before any project modification. The staging directory is
    # temporary, private to this run, and always removed when the run exits.
    with tempfile.TemporaryDirectory(prefix=".agent_cli_install_", dir=root) as backup_dir:
        backups = Path(backup_dir)
        for i, change in enumerate(changes):
            if change.existed:
                snapshot = backups / str(i)
                shutil.copy2(change.destination, snapshot)
                mode = stat.S_IMODE(change.destination.stat().st_mode)
            else:
                snapshot, mode = None, None
            journal.append((change.destination, snapshot, mode))
        try:
            for change, (_, _, mode) in zip(changes, journal):
                checked_path(root, change.relative)  # detect changed paths at write time
                _ensure_dirs(change.destination.parent, root, created_dirs)
                _atomic_write(change.destination, change.content, mode)
            command = [sys.executable, "-B", str(root / str(plan["entrypoint"])), "system-docgen", "--json"]
            if plan["docgen_dry_run"]:
                command.append("--dry-run")
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(command, cwd=root, text=True, capture_output=True,
                                    encoding="utf-8", errors="replace", timeout=30, env=env)
            if result.returncode:
                raise RuntimeError(f"system-docgen failed: {result.stdout[:500]} {result.stderr[:500]}")
            parsed = json.loads(result.stdout)
            if parsed.get("result", {}).get("status") != "ok":
                raise RuntimeError("system-docgen returned non-ok status")
        except Exception as exc:
            rollback_errors = _restore(journal, created_dirs)
            if rollback_errors:
                raise RuntimeError(f"Installation failed ({type(exc).__name__}); rollback incomplete: {rollback_errors}") from exc
            raise RuntimeError(f"Installation failed and original files restored: {type(exc).__name__}: {exc}") from exc

    return {
        **plan,
        "dry_run": False,
        "installation_state": "FILES_INSTALLED",
        "created": [c.relative for c in changes if not c.existed],
        "overwritten": [c.relative for c in changes if c.existed],
        "gitignore_updated": bool(extra),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely install reusable zero-dependency agent CLI")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Existing destination project")
    parser.add_argument("--layout", choices=VALID_LAYOUTS, default="auto",
                        help="auto: isolate occupied roots, preserve existing installations; flat: legacy; isolated: tools/ runtime")
    parser.add_argument("--force", action="store_true", help="Replace existing starter files (never foreign entrypoints or existing AGENTS.md)")
    parser.add_argument("--integrate-agents", action="store_true",
                        help="Append managed CLI guidance to existing root AGENTS.md without replacing its rules")
    parser.add_argument("--dry-run", action="store_true", help="Plan changes without writing to the project")
    parser.add_argument("--ref", default="main", help="Source revision: main or a full immutable Git commit SHA")
    parser.add_argument("--json", action="store_true", help="Return result as JSON")
    args = parser.parse_args()
    try:
        outcome = install(args.target, force=args.force, dry_run=args.dry_run,
                          revision=args.ref, integrate_agents=args.integrate_agents,
                          layout=args.layout)
        if args.json:
            sys.stdout.write(json.dumps(outcome, ensure_ascii=False) + "\n")
        elif args.dry_run:
            sys.stdout.write("No files changed. Proposed changes:\n")
            sys.stdout.write(f"  create: {len(outcome['planned_created'])}, overwrite: {len(outcome['planned_overwritten'])}, skip: {len(outcome['skipped'])}\n")
        else:
            sys.stdout.write(f"Agent CLI ready: python {outcome['entrypoint']} sys-info --json\n")
            sys.stdout.write(f"Created {len(outcome['created'])}, overwritten {len(outcome['overwritten'])}, skipped {len(outcome['skipped'])}\n")
        if not args.json:
            if outcome["guidance_state"] == "existing_preserved":
                sys.stdout.write("Existing AGENTS.md preserved. To link project CLI guidance, review and use --integrate-agents.\n")
            if outcome["codex_override_present"]:
                sys.stdout.write("Note: root AGENTS.override.md exists; Codex may load it instead of AGENTS.md. Review separately.\n")
        return 0
    except (OSError, ValueError, RuntimeError, UnicodeError, urllib.error.URLError,
            subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Installation failed: {type(exc).__name__}: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
