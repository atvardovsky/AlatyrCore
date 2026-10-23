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


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen_options", set())
        if self.dest in seen:
            parser.error(f"{option_string} may be supplied only once")
        setattr(namespace, "_seen_options", seen | {self.dest})
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    presence = subparsers.add_parser("session-presence", allow_abbrev=False)
    presence.add_argument("--target", type=Path, required=True, action=Once)
    presence.add_argument("--framework-source", type=Path, action=Once)
    presence.add_argument("arguments", nargs=argparse.REMAINDER)
    cooperation = subparsers.add_parser("cooperation-preflight", allow_abbrev=False)
    add_common(cooperation)
    cooperation.add_argument("--scope", action="append", default=[])
    cooperation.add_argument("--command", action="append", default=[])
    cooperation.add_argument("--session-uid")
    for name in ("status", "doctor", "archive-audit"):
        operation = subparsers.add_parser(name, allow_abbrev=False)
        add_common(operation)
        if name == "doctor":
            operation.add_argument("--incident-frontier", action="store_true")
        if name in {"status", "doctor"}:
            operation.add_argument("--current-task")
        if name == "archive-audit":
            operation.add_argument("--historical-evidence-index", type=Path, action=Once)

    current = subparsers.add_parser("validate-current", allow_abbrev=False)
    add_common(current)
    current.add_argument("--diff-ref", required=True)
    current.add_argument("--task-id")
    current.add_argument("--task-class", choices=["small-task", "standard-task", "large-or-resumable", "protected-or-sensitive"])
    current.add_argument("--problem-model", action="append", default=[])
    current.add_argument("--require-task-acceptance", action="store_true")
    current.add_argument("--approval-record", action="append", required=True)
    current.add_argument("--change-package", action="append", default=[])
    current.add_argument("--historical-evidence-index", type=Path, action=Once)

    finalize = subparsers.add_parser("finalize-support", allow_abbrev=False)
    add_common(finalize)
    finalize.add_argument("--write", action="store_true")
    finalize.add_argument("--migration-staging", action="store_true")
    finalize.add_argument("--diff-ref")
    finalize.add_argument("--approval-record", action="append", default=[])
    finalize.add_argument("--change-package", action="append", default=[])
    finalize.add_argument("--historical-evidence-index", type=Path, action=Once)
    finalize.add_argument("--require-current-change", action="store_true")
    finalize.add_argument("--task-id")
    finalize.add_argument("--task-class", choices=["small-task", "standard-task", "large-or-resumable", "protected-or-sensitive"])
    finalize.add_argument("--problem-model", action="append", default=[])
    finalize.add_argument("--require-task-acceptance", action="store_true")
    return parser


def canonical_arguments(args: argparse.Namespace, target: Path, source: Path) -> list[str]:
    if args.operation == "session-presence":
        return ["session-presence", "--target", str(target), *args.arguments]
    if args.operation == "cooperation-preflight":
        command = ["cooperation-preflight", "--target", str(target)]
        for name in ("scope", "command"):
            for value in getattr(args, name):
                command.extend(["--" + name, value])
        if args.session_uid:
            command.extend(["--session-uid", args.session_uid])
        return command
    common = ["--target", str(target), "--framework-source", str(source)]
    if args.operation in {"status", "doctor"}:
        extra = ["--incident-frontier"] if args.operation == "doctor" and args.incident_frontier else []
        if args.current_task:
            extra.extend(["--current-task", args.current_task])
        return [args.operation, *common, *extra]
    if args.operation == "archive-audit":
        command = [
            "validate-adapter",
            *common,
            "--validation-phase",
            "acceptance",
            "--validation-scope",
            "full",
            "--approval-archive-mode",
            "full",
        ]
        if getattr(args, "historical_evidence_index", None) is not None:
            command.extend(["--historical-evidence-index", str(args.historical_evidence_index)])
        return command
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
        if getattr(args, "task_id", None):
            command.extend(["--task-id", args.task_id])
        if getattr(args, "task_class", None):
            command.extend(["--task-class", args.task_class])
        for model in getattr(args, "problem_model", []):
            command.extend(["--problem-model", model])
        if getattr(args, "require_task_acceptance", False):
            command.append("--require-task-acceptance")
        for package in args.change_package:
            command.extend(["--change-package", package])
        if args.change_package:
            command.append("--enforce-change-package")
        if getattr(args, "historical_evidence_index", None) is not None:
            command.extend(["--historical-evidence-index", str(args.historical_evidence_index)])
        # Canonical acceptance resolves enabled modules and enforces their packages.
        command.append("--enforce-approval-scope")
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
    if getattr(args, "historical_evidence_index", None) is not None:
        command.extend(["--historical-evidence-index", str(args.historical_evidence_index)])
    if args.require_current_change:
        command.append("--require-current-change")
    for name in ("task_id", "task_class"):
        if getattr(args, name, None):
            command.extend(["--" + name.replace("_", "-"), getattr(args, name)])
    for model in getattr(args, "problem_model", []):
        command.extend(["--problem-model", model])
    if getattr(args, "require_task_acceptance", False):
        command.append("--require-task-acceptance")
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
