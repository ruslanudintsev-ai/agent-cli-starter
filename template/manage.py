#!/usr/bin/env python3
# AGENT_CLI_STARTER_ENTRYPOINT
"""Agent CLI Starter: safe command discovery and structured execution."""

from __future__ import annotations

import argparse
import contextlib
import importlib
import inspect
import pkgutil
import re
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass

from core.commands.base import BaseCommand, _BoundedWriter  # noqa: E402


def discover_commands() -> tuple[dict[str, BaseCommand], list[str]]:
    """Import modules independently; a broken plugin cannot break other commands.

    This is exception isolation, NOT a security sandbox for untrusted Python.
    """
    directory = Path(__file__).resolve().parent / "core" / "commands"
    commands: dict[str, BaseCommand] = {}
    warnings: list[str] = []
    for info in sorted(pkgutil.iter_modules([str(directory)]), key=lambda item: item.name):
        if info.name.startswith("_") or info.name == "base" or info.ispkg:
            continue
        try:
            with contextlib.redirect_stdout(_BoundedWriter()), contextlib.redirect_stderr(_BoundedWriter()):
                module = importlib.import_module(f"core.commands.{info.name}")
                command_types = [
                    cls for _, cls in inspect.getmembers(module, inspect.isclass)
                    if cls.__module__ == module.__name__
                    and issubclass(cls, BaseCommand) and cls is not BaseCommand
                    and not inspect.isabstract(cls)
                ]
                for cls in command_types:
                    command = cls()
                    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", command.name):
                        raise ValueError(f"Invalid command name: {command.name!r}")
                    if command.name in commands:
                        raise ValueError(f"Duplicate command name: {command.name}")
                    commands[command.name] = command
        except Exception as exc:
            warnings.append(f"{info.name}: {type(exc).__name__}: {str(exc)[:300]}")
    return commands, warnings


def make_parser() -> tuple[argparse.ArgumentParser, dict[str, BaseCommand],
                           dict[str, argparse.ArgumentParser], list[str]]:
    parser = argparse.ArgumentParser(description="Zero-dependency agent project CLI")
    parser.add_argument("--json", action="store_true", help="Machine-readable response")
    subparsers = parser.add_subparsers(dest="_command_name", required=True)
    commands, warnings = discover_commands()
    registered: dict[str, BaseCommand] = {}
    configured: dict[str, argparse.ArgumentParser] = {}
    for name, command in sorted(commands.items()):
        try:
            sub = subparsers.add_parser(name, description=command.description, help=command.description)
            sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                             help="Machine-readable response")
            command.configure_parser(sub)
            registered[name] = command
            configured[name] = sub
        except Exception as exc:
            subparsers.choices.pop(name, None)
            warnings.append(f"{name}: argparse setup failed: {type(exc).__name__}: {str(exc)[:300]}")
    return parser, registered, configured, warnings


def main(argv: list[str] | None = None) -> int:
    parser, commands, subparsers, warnings = make_parser()
    args = parser.parse_args(argv)
    args._subparsers = subparsers
    args._discovery_warnings = warnings
    script = Path(__file__).resolve()
    try:
        args._entrypoint = script.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        args._entrypoint = script.name
    command = commands.get(args._command_name)
    if command is None:
        parser.error("Unknown or unavailable command")
    return command.execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
