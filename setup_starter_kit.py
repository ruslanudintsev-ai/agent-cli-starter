#!/usr/bin/env python3
"""Standalone, dependency-free installer for agent-cli-starter (Python 3.10+).

When run from a repository checkout, reads local template/. When downloaded by
install.sh, fetches the template files directly from the public GitHub repo.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAW_TEMPLATE = "https://raw.githubusercontent.com/ruslanudintsev-ai/agent-cli-starter/main/template"
TEMPLATE_FILES = (
    ".agents/rules/cli-standard.md",
    ".agents/rules/self-learning.md",
    ".agents/skills/cli-tools/SKILL.md",
    ".agents/skills/cli-tools/gotchas.md",
    ".cursor/rules/agent-cli.mdc",
    "AGENTS.md",
    "CLAUDE.md",
    "AIDER_CONVENTIONS.md",
    "core/__init__.py",
    "core/commands/__init__.py",
    "core/commands/base.py",
    "core/commands/sys_info.py",
    "core/commands/system_docgen.py",
    "core/commands/dev_scaffold.py",
    "core/commands/dev_validate.py",
    "manage.py",
)
IGNORE_LINES = (".cle_state/", ".cle_cache/", "__pycache__/")
MARKER = "# AGENT_CLI_STARTER_ENTRYPOINT"


def select_entrypoint(target: Path) -> str:
    """Never replace a foreign manage.py, even if --force is supplied."""
    existing = target / "manage.py"
    if not existing.exists():
        return "manage.py"
    try:
        if MARKER in existing.read_text(encoding="utf-8", errors="replace"):
            return "manage.py"
    except OSError:
        pass
    return "agent_cli.py"


def load_templates() -> dict[str, str]:
    local = (Path(__file__).resolve().parent / "template") if "__file__" in globals() else None
    result: dict[str, str] = {}
    for relative in TEMPLATE_FILES:
        if local is not None and (local / relative).is_file():
            content = (local / relative).read_text(encoding="utf-8")
        else:
            url = f"{RAW_TEMPLATE}/{relative}"
            with urllib.request.urlopen(url, timeout=25) as response:
                content = response.read().decode("utf-8")
        result[relative] = content
    return result


def update_gitignore(target: Path) -> bool:
    path = target / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    existing = {line.strip() for line in current.splitlines()}
    missing = [line for line in IGNORE_LINES if line not in existing]
    if not missing:
        return False
    content = current + ("\n" if current and not current.endswith("\n") else "")
    content += "\n".join(missing) + "\n"
    path.write_text(content, encoding="utf-8")
    return True


def install(target: Path, force: bool = False) -> dict[str, object]:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required")
    target = target.resolve()
    if not target.is_dir() or target == Path(target.anchor):
        raise ValueError("--target must be an existing project directory, not filesystem root")
    entrypoint = select_entrypoint(target)
    source = load_templates()  # Complete all network reads before changing the project.
    created: list[str] = []
    overwritten: list[str] = []
    skipped: list[str] = []
    skill_path = ".agents/skills/cli-tools/SKILL.md"
    for relative, content in source.items():
        destination_relative = entrypoint if relative == "manage.py" else relative
        destination = target / destination_relative
        if destination.exists() and not force:
            skipped.append(destination_relative)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = content.replace("__ENTRYPOINT__", entrypoint)
        existed = destination.exists()
        destination.write_text(text, encoding="utf-8", newline="\n")
        (overwritten if existed else created).append(destination_relative)
    gitignore_updated = update_gitignore(target)
    # Never rewrite an existing SKILL.md unless --force explicitly allowed it.
    dry_run = skill_path in skipped
    command = [sys.executable, str(target / entrypoint), "system-docgen", "--json"]
    if dry_run:
        command.append("--dry-run")
    process = subprocess.run(command, cwd=target, text=True, capture_output=True,
                             encoding="utf-8", errors="replace", timeout=30)
    if process.returncode:
        raise RuntimeError(f"system-docgen failed: {process.stdout[:1000]} {process.stderr[:1000]}")
    doc_result = json.loads(process.stdout)
    if doc_result["result"].get("status") != "ok":
        raise RuntimeError("system-docgen returned an error")
    return {"status": "ok", "entrypoint": entrypoint, "created": created,
            "overwritten": overwritten, "skipped": skipped,
            "gitignore_updated": gitignore_updated,
            "docgen_dry_run": dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install reusable zero-dependency agent CLI")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Existing destination project")
    parser.add_argument("--force", action="store_true", help="Overwrite starter files (not foreign manage.py)")
    parser.add_argument("--json", action="store_true", help="Return installation result as JSON")
    args = parser.parse_args()
    try:
        result = install(args.target, args.force)
        if args.json:
            sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(f"Installed agent CLI: python {result['entrypoint']} sys-info --json\n")
            sys.stdout.write(f"Created {len(result['created'])}, skipped {len(result['skipped'])} files\n")
        return 0
    except (OSError, ValueError, RuntimeError, UnicodeError, urllib.error.URLError,
            subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Installation failed: {type(exc).__name__}: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
