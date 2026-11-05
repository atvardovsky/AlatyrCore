#!/usr/bin/env python3
"""Capture or compare adopted material test inputs; never run tests or write files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plan_test_resources import resolved_test_policy
from target_adapter_validation.context import TargetRepositoryView
from test_input_state import state_report
from test_selection import read_selection_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--test-file", action="append", default=[])
    parser.add_argument("--before", help="Target-relative UTF-8 JSON capture retained by the authorized target runner.")
    args = parser.parse_args()
    try:
        view = TargetRepositoryView(args.target.resolve())
        policy = resolved_test_policy(view)
        command = next((item for item in policy["commands"] if item["id"] == args.command), None)
        if command is None:
            raise ValueError("select a command from the canonical target testing policy")
        before = read_selection_json(view, args.before) if args.before is not None else None
        if args.before is not None and not isinstance(before, dict):
            raise ValueError("before snapshot must be a captured JSON object")
        report = state_report(view, policy, command, args.test_file, before)
        if view.finalize():
            raise ValueError("test input state changed during observation; recapture")
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 1 if report["state"] == "changed" else 0
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"state": "unavailable", "error": str(exc), "execution_performed": False,
                          "authorization_granted": False, "acceptance_granted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
