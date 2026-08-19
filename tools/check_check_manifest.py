#!/usr/bin/env python3
"""Validate source-check manifest coverage and selection contracts."""

from __future__ import annotations

import sys
from pathlib import Path

from check_all import load_manifest, matches


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_CHECKERS = {"check_all.py", "check_check_manifest.py"}


def main() -> int:
    failures: list[str] = []
    try:
        checks = load_manifest()
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    commands = [check["command"] for check in checks]
    represented = {Path(command[0]).name for command in commands}
    checker_files = {
        path.name
        for path in (ROOT / "tools").glob("check_*.py")
        if path.name not in EXCLUDED_CHECKERS
    }
    missing = sorted(checker_files - represented)
    if missing:
        failures.append(f"checker scripts missing from manifest: {missing}")

    for check in checks:
        script = check["command"][0]
        if not matches(check, script):
            failures.append(f"{check['id']} owned_paths do not include its script")
        if "release" in check["profiles"] and check["id"] != "release-drift-release" and (
            "full" not in check["profiles"]
        ):
            failures.append(f"release-only helper is not an approved release gate: {check['id']}")

    drift_commands = [
        command for command in commands if command[0] == "tools/check_release_drift.py"
    ]
    if not any("change" in command for command in drift_commands):
        failures.append("check manifest omits change-baseline release drift")
    if not any("release" in command for command in drift_commands):
        failures.append("check manifest omits tag-baseline release drift")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: checked {len(checks)} manifest check entries and checker coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
