#!/usr/bin/env python3
"""Materialize seed-only conformance fixture repositories.

This source-repository helper creates target-shaped fixture directories from
`conformance/fixtures/*/fixture.json`. It does not scaffold Alatyr, run an
assistant, install an adapter, or validate a target project.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "conformance" / "fixtures"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def fixture_dirs(selected: list[str]) -> list[Path]:
    dirs = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
    if not selected:
        return dirs
    selected_set = set(selected)
    result = [path for path in dirs if path.name in selected_set]
    missing = sorted(selected_set - {path.name for path in result})
    if missing:
        raise ValueError(f"unknown fixture(s): {', '.join(missing)}")
    return result


def write_seed_files(target: Path, fixture: dict[str, Any]) -> list[str]:
    written: list[str] = []
    for seed in fixture["seed_files"]:
        relpath = Path(seed["path"])
        if relpath.is_absolute() or ".." in relpath.parts:
            raise ValueError(f"unsafe seed path: {relpath}")
        path = target / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(seed["content"], encoding="utf-8")
        written.append(relpath.as_posix())
    return sorted(written)


def materialize_fixture(
    fixture_dir: Path,
    output: Path,
    *,
    overwrite: bool,
) -> tuple[str, list[str]]:
    fixture = load_json(fixture_dir / "fixture.json")
    fixture_name = fixture["fixture"]
    target = output / fixture_name

    if target.exists():
        if not overwrite:
            raise ValueError(
                f"fixture output already exists: {target}; use --overwrite to replace it"
            )
        if not target.is_dir():
            raise ValueError(f"fixture output exists and is not a directory: {target}")
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=False)
    written = write_seed_files(target, fixture)
    return fixture_name, written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create seed-only conformance fixture repositories."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where fixture repositories will be created.",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Fixture name to materialize. May be provided more than once.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing fixture output directories.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    try:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for fixture_dir in fixture_dirs(args.fixture):
            name, written = materialize_fixture(
                fixture_dir,
                output,
                overwrite=args.overwrite,
            )
            print(f"OK: materialized {name} with {len(written)} seed files")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"OK: fixture repositories available under {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
