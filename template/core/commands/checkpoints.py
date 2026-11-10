"""Privacy-conscious read-only listing and opt-in expiry cleanup for checkpoints."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.commands.base import BaseCommand
from core.state import CheckpointStore


class CheckpointsCommand(BaseCommand):
    name = "checkpoints"
    description = "List checkpoint metadata or prune expired entries (never show payloads)"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--action", choices=("list", "prune"), default="list",
                            help="List metadata or preview/apply expiry cleanup")
        parser.add_argument("--apply", action="store_true", help="Allow removal of expired entries during --action prune")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        store = CheckpointStore(Path.cwd())
        if args.apply and args.action != "prune":
            return {"status": "error", "message": "--apply requires --action prune"}
        if args.action == "prune":
            names = store.prune(apply=args.apply)
            return {"status": "ok", "action": "prune", "applied": args.apply,
                    "expired_count": len(names), "names": names}
        entries = store.list_metadata()
        return {"status": "ok", "action": "list", "count": len(entries), "entries": entries}
