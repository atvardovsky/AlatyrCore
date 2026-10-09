#!/usr/bin/env python3
"""Resolve AlatyrCore locally and invoke a bounded canonical operation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


LOCAL_SOURCE = Path(".ai/local/framework-source")


def resolve_source(target: Path, explicit: Path | None) -> Path:
    candidates: list[tuple[str, Path, Path | None]] = []
    if explicit is not None:
        candidates.append(("--framework-source", explicit, None))
    environment = os.environ.get("ALATYR_CORE")
    if environment:
        candidates.append(("ALATYR_CORE", Path(environment), None))
    local_config = target / LOCAL_SOURCE
    if local_config.is_file():
        value = local_config.read_text(encoding="utf-8").strip()
        if value:
            candidates.append((LOCAL_SOURCE.as_posix(), Path(value), target))

    for source_name, candidate, relative_base in candidates:
        expanded = candidate.expanduser()
        if not expanded.is_absolute() and relative_base is not None:
            expanded = relative_base / expanded
        resolved = expanded.resolve()
        if (resolved / "tools/alatyr.py").is_file():
            return resolved
        raise ValueError(
            f"{source_name} does not identify an AlatyrCore source checkout: {resolved}"
        )
    raise ValueError(
        "AlatyrCore source is unresolved; provide --framework-source, set "
        "ALATYR_CORE, or write its path to .ai/local/framework-source"
    )


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", type=Path, default=Path("."))
    parser.add_argument("--framework-source", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for name in ("status", "doctor", "archive-audit"):
        add_common(subparsers.add_parser(name, allow_abbrev=False))

    current = subparsers.add_parser("validate-current", allow_abbrev=False)
    add_common(current)
    current.add_argument("--diff-ref", required=True)
    current.add_argument("--approval-record", action="append", required=True)
    current.add_argument("--change-package", action="append", required=True)

    finalize = subparsers.add_parser("finalize-support", allow_abbrev=False)
    add_common(finalize)
    finalize.add_argument("--write", action="store_true")
    finalize.add_argument("--migration-staging", action="store_true")
    finalize.add_argument("--diff-ref")
    finalize.add_argument("--approval-record", action="append", default=[])
    finalize.add_argument("--change-package", action="append", default=[])
    finalize.add_argument("--require-current-change", action="store_true")
    return parser


def canonical_arguments(args: argparse.Namespace, target: Path, source: Path) -> list[str]:
    common = ["--target", str(target), "--framework-source", str(source)]
    if args.operation in {"status", "doctor"}:
        return [args.operation, *common]
    if args.operation == "archive-audit":
        return [
            "validate-adapter",
            *common,
            "--validation-phase",
            "acceptance",
            "--validation-scope",
            "full",
            "--approval-archive-mode",
            "full",
        ]
    if args.operation == "validate-current":
        command = [
            "validate-adapter",
            *common,
            "--validation-phase",
            "acceptance",
            "--validation-scope",
            "full",
            "--approval-archive-mode",
            "full",
            "--diff-ref",
            args.diff_ref,
        ]
        for record in args.approval_record:
            command.extend(["--approval-record", record])
        for package in args.change_package:
            command.extend(["--change-package", package])
        command.extend(["--enforce-approval-scope", "--enforce-change-package"])
        return command

    command = ["finalize-support", "--target", str(target)]
    if args.write:
        command.append("--write")
    if args.migration_staging:
        command.append("--migration-staging")
    if args.diff_ref:
        command.extend(["--diff-ref", args.diff_ref])
    for record in args.approval_record:
        command.extend(["--approval-record", record])
    for package in args.change_package:
        command.extend(["--change-package", package])
    if args.require_current_change:
        command.append("--require-current-change")
    return command


def main() -> int:
    args = build_parser().parse_args()
    target = args.target.resolve()
    try:
        source = resolve_source(target, args.framework_source)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    command = [
        sys.executable,
        str(source / "tools/alatyr.py"),
        *canonical_arguments(args, target, source),
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
