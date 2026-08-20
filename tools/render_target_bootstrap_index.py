#!/usr/bin/env python3
"""Render or check the hash-bound compact bootstrap index for a target adapter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bootstrap_index import BOOTSTRAP_PATH, build_from_target, render


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    target = args.target.resolve()
    try:
        expected = render(build_from_target(target))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    output = target / BOOTSTRAP_PATH
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(expected.encode("utf-8"))
        print(f"Wrote bootstrap index: {output}")
        return 0
    if args.check or not args.stdout:
        try:
            actual = output.read_bytes()
        except OSError as exc:
            print(f"FAIL: cannot read {output}: {exc}", file=sys.stderr)
            return 1
        if actual != expected.encode("utf-8"):
            print(f"FAIL: bootstrap index is stale: {output}", file=sys.stderr)
            return 1
        print(f"OK: bootstrap index matches canonical sources: {output}")
        return 0
    print(expected, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
