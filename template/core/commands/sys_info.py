"""Portable system overview, using psutil only when already installed."""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import subprocess
import sys
from collections.abc import Mapping
from typing import Any

from core.commands.base import BaseCommand, psutil


def total_physical_ram_mb() -> float | None:
    """Try psutil, Linux/POSIX sysconf, Windows API, and macOS sysctl."""
    if psutil is not None:
        try:
            return round(psutil.virtual_memory().total / (1024 * 1024), 2)
        except (OSError, ValueError, AttributeError):
            pass
    if sys.platform == "win32":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys / (1024 * 1024), 2)
        except (OSError, AttributeError):
            pass
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024), 2)
    except (AttributeError, OSError, ValueError):
        pass
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True,
                timeout=2, check=True,
            )
            return round(int(result.stdout.strip()) / (1024 * 1024), 2)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return None


class SysInfoCommand(BaseCommand):
    name = "sys-info"
    description = "OS, Python interpreter and physical RAM diagnostics"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--details", action="store_true", help="Include executable and CPU count")

    def run(self, args: argparse.Namespace) -> Mapping[str, Any]:
        info: dict[str, Any] = {
            "status": "ok", "os": platform.platform(), "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "ram_total_mb": total_physical_ram_mb(), "psutil_available": psutil is not None,
        }
        if args.details:
            info.update({"python_executable": sys.executable, "cpu_count": os.cpu_count()})
        return info
