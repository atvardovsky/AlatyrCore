#!/usr/bin/env python3
"""Check or render the target approval archive digest index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from approval_archive import INDEX_PATH, build_archive_index
from target_tool_compat import assert_write_compatible


def render(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    expected = render(build_archive_index(target))
    output = target / INDEX_PATH
    if args.write:
        try:
            assert_write_compatible(
                target,
                tool_name="render_approval_archive_index.py",
                migration_staging=args.migration_staging,
            )
        except (OSError, ValueError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected, encoding="utf-8")
        print(f"Wrote {INDEX_PATH.as_posix()}")
        return 0
    if not output.is_file() or output.read_text(encoding="utf-8") != expected:
        print(f"FAIL: missing or stale {INDEX_PATH.as_posix()}", file=sys.stderr)
        return 1
    print(f"OK: checked {INDEX_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
