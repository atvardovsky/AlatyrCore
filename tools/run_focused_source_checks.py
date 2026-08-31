#!/usr/bin/env python3
"""Run focused AlatyrCore source checks for small local changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from check_all import default_changed_from as check_all_default_changed_from

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def default_changed_from() -> str:
    return check_all_default_changed_from()


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--changed-from",
        help=(
            "Baseline for changed-path source-check selection. Defaults to "
            "origin/main when available, otherwise HEAD."
        ),
    )
    argument_parser.add_argument(
        "--from-ref",
        help="Baseline substituted into checks that need a semantic diff reference.",
    )
    argument_parser.add_argument(
        "--jobs",
        type=int,
        help="Worker count passed to tools/check_all.py.",
    )
    argument_parser.add_argument(
        "--report",
        type=Path,
        help="Write the machine-readable check_all.py report to this path.",
    )
    argument_parser.add_argument(
        "--list",
        action="store_true",
        help="List the selected focused check commands without running them.",
    )
    return argument_parser


def check_all_command(args: argparse.Namespace) -> tuple[str, list[str]]:
    changed_from = args.changed_from or default_changed_from()
    command = [
        sys.executable,
        str(TOOLS / "check_all.py"),
        "--profile",
        "fast",
        "--changed-from",
        changed_from,
    ]
    if args.from_ref:
        command.extend(["--from-ref", args.from_ref])
    if args.jobs is not None:
        command.extend(["--jobs", str(args.jobs)])
    if args.report:
        command.extend(["--report", str(args.report)])
    if args.list:
        command.append("--list")
    return changed_from, command


def main(argv: list[str] | None = None) -> int:
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.jobs is not None and args.jobs <= 0:
        argument_parser.error("--jobs must be positive")

    changed_from, command = check_all_command(args)
    print(
        "INFO: running focused source checks with "
        f"`tools/check_all.py --profile fast --changed-from {changed_from}`",
        flush=True,
    )
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
