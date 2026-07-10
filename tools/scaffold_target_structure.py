#!/usr/bin/env python3
"""Scaffold Alatyr target adapter structure from source templates.

This is a source-repository helper, not the Alatyr installation mechanism.
It copies placeholder files only. It does not inspect target facts, accept an
installation, overwrite existing files by default, or make protected decisions.

The implementation uses only Python standard-library APIs so it can run on
Linux, macOS, and Windows with Python 3.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "target"
FRAMEWORK_ROOT = ROOT / "framework"


def iter_template_files() -> list[Path]:
    return sorted(path for path in TEMPLATE_ROOT.rglob("*") if path.is_file())


def iter_framework_files() -> list[Path]:
    return sorted(
        path
        for path in FRAMEWORK_ROOT.iterdir()
        if path.is_file() and path.suffix in {".md", ".json"}
    )


def copy_file(src: Path, dst: Path, *, write: bool) -> None:
    if write:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def plan(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    target = args.target.resolve()
    actions: list[str] = []
    blocked: list[str] = []

    if not target.exists():
        blocked.append(f"target does not exist: {target}")
        return actions, blocked
    if not target.is_dir():
        blocked.append(f"target is not a directory: {target}")
        return actions, blocked

    for src in iter_template_files():
        rel = src.relative_to(TEMPLATE_ROOT)
        dst = target / rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(src, dst, write=args.write)
        actions.append(f"template: {rel} -> {dst}")

    for src in iter_framework_files():
        rel = Path(".ai") / "framework" / src.name
        dst = target / rel
        if dst.exists() and not args.overwrite_existing:
            blocked.append(f"exists, would not overwrite: {dst}")
            continue
        copy_file(src, dst, write=args.write)
        actions.append(f"framework: {src.name} -> {dst}")

    return actions, blocked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold placeholder Alatyr adapter files. Default mode is dry-run."
        ),
        epilog=(
            "Examples:\n"
            "  Linux/macOS: python3 tools/scaffold_target_structure.py "
            "--target /path/to/repo\n"
            "  Windows: py -3 tools\\scaffold_target_structure.py "
            "--target C:\\path\\repo\n"
            "  Windows cmd wrapper: tools\\scaffold_target_structure.cmd "
            "--target C:\\path\\repo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="Existing target repository directory.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write files. Without this flag the helper prints the plan only.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help=(
            "Overwrite existing files. Use only after explicit human approval "
            "for the exact target path and protected surfaces."
        ),
    )
    args = parser.parse_args()

    actions, blocked = plan(args)

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"Alatyr scaffold mode: {mode}")
    print("This helper does not complete installation or fill target facts.")
    print("Supported platforms: Linux, macOS, Windows.")

    if actions:
        print("\nActions:")
        for action in actions:
            print(f"- {action}")

    if blocked:
        print("\nBlocked or skipped:")
        for item in blocked:
            print(f"- {item}")

    if args.write and blocked and not args.overwrite_existing:
        print(
            "\nSome files were skipped because they already exist. "
            "Review target facts and approvals before overwriting.",
            file=sys.stderr,
        )

    return 1 if blocked and not actions else 0


if __name__ == "__main__":
    raise SystemExit(main())
