#!/usr/bin/env python3
"""Check or explicitly refresh one target adapter support state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from support_state import (
    STATE_PATH,
    SupportStateError,
    build_support_state,
    load_state,
    render_state,
    state_differences,
    state_is_current,
)
from target_tool_compat import assert_write_compatible


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Refresh the generated state; otherwise perform a read-only check.",
    )
    parser.add_argument(
        "--migration-staging",
        action="store_true",
        help="Allow writes while an explicit target adapter migration is in progress.",
    )
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        current = build_support_state(target)
    except SupportStateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    state_path = target / STATE_PATH
    if args.write:
        try:
            assert_write_compatible(
                target,
                tool_name="snapshot_target_support.py",
                migration_staging=args.migration_staging,
            )
        except (OSError, ValueError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_bytes(render_state(current).encode("utf-8"))
        print(
            f"Wrote {STATE_PATH} with {len(current['files'])} managed support files"
        )
        return 0
    try:
        recorded = load_state(target)
    except SupportStateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if not state_is_current(recorded, current):
        for difference in state_differences(recorded, current):
            print(f"FAIL: {difference.change} {difference.path}", file=sys.stderr)
        if recorded.get("policy_digest") != current.get("policy_digest"):
            print("FAIL: support policy digest changed", file=sys.stderr)
        print(
            "Repair with explicit adapter-write authorization: "
            f"snapshot_target_support.py --target {target} --write",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK: support state covers {len(current['files'])} files in "
        f"{len(current['groups'])} groups"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
