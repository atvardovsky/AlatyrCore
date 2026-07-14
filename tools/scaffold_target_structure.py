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
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "target"
FRAMEWORK_ROOT = ROOT / "framework"
PROFILE_MANIFEST = ROOT / "tools" / "scaffold_profiles.json"


def load_profile_manifest() -> dict[str, Any]:
    data = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scaffold profile manifest must be a JSON object")
    return data


def profile_names() -> list[str]:
    profiles = load_profile_manifest().get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("scaffold profile manifest must define profiles")
    return list(profiles)


def resolve_profile_paths(profile: str) -> set[Path]:
    manifest = load_profile_manifest()
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or profile not in profiles:
        raise ValueError(f"unknown scaffold profile: {profile}")

    resolving: set[str] = set()

    def resolve(name: str) -> set[Path]:
        if name in resolving:
            raise ValueError(f"cyclic scaffold profile inheritance: {name}")
        entry = profiles.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"invalid scaffold profile: {name}")
        resolving.add(name)
        paths: set[Path] = set()
        parent = entry.get("extends")
        if parent is not None:
            if not isinstance(parent, str) or parent not in profiles:
                raise ValueError(f"invalid parent for scaffold profile: {name}")
            paths.update(resolve(parent))
        items = entry.get("template_files", [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"invalid template_files for scaffold profile: {name}")
        paths.update(Path(item) for item in items)
        if entry.get("include_remaining_template_files") is True:
            paths.update(
                path.relative_to(TEMPLATE_ROOT)
                for path in TEMPLATE_ROOT.rglob("*")
                if path.is_file()
            )
        resolving.remove(name)
        return paths

    return resolve(profile)


def iter_template_files(profile: str = "full") -> list[Path]:
    return sorted(TEMPLATE_ROOT / relpath for relpath in resolve_profile_paths(profile))


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
    profile = getattr(args, "profile", "full")
    actions: list[str] = []
    blocked: list[str] = []

    if not target.exists():
        blocked.append(f"target does not exist: {target}")
        return actions, blocked
    if not target.is_dir():
        blocked.append(f"target is not a directory: {target}")
        return actions, blocked

    for src in iter_template_files(profile):
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
        "--profile",
        choices=profile_names(),
        default="full",
        help=(
            "Target adapter support profile. core installs required adapter "
            "surfaces, standard adds common lifecycle/product operations, and "
            "full preserves the historical all-template behavior."
        ),
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
    print(f"Alatyr scaffold profile: {args.profile}")
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
