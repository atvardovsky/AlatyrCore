#!/usr/bin/env python3
"""Report target support-surface drift without changing repository state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from support_state import SupportStateError, build_support_state, load_state, state_differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        recorded = load_state(target)
        current = build_support_state(target)
    except SupportStateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    differences = state_differences(recorded, current)
    report = {
        "schema_version": 1,
        "report_kind": "target-support-diff",
        "baseline_digest": recorded.get("root_digest"),
        "current_digest": current.get("root_digest"),
        "differences": [difference.__dict__ for difference in differences],
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered.encode("utf-8"))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
