#!/usr/bin/env python3
"""Check or refresh opted-in module activation projections, preserving rationale."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import sys
from pathlib import Path

from target_adapter_validation.module_profile import state_projection
from target_tool_compat import assert_write_compatible
from support_write_transaction import SupportTransaction, support_writer_lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        if args.write:
            assert_write_compatible(target, tool_name="render_module_profile.py", migration_staging=args.migration_staging)
        with support_writer_lock(target) if args.write else nullcontext():
            planned = state_projection(target, migration_staging=args.migration_staging)
            if planned is None:
                return 0
            if args.write:
                SupportTransaction(target).apply({planned.path: planned.desired}, expected_inputs=planned.inputs)
            elif planned.before != planned.desired:
                print("FAIL: module-profile activation projection is stale", file=sys.stderr)
                return 1
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"FAIL: module-state projection: {exc}", file=sys.stderr)
        return 2
    print("OK: module-profile activation projection; target rationale preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
