#!/usr/bin/env python3
"""Inspect or explicitly maintain advisory local session presence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from session_presence_contract import ACTIVITIES
from session_presence_store import operate


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen_options", set())
        if self.dest in seen:
            parser.error(f"{option_string} may be supplied only once")
        setattr(namespace, "_seen_options", seen | {self.dest})
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path, action=Once)
    parser.add_argument("--source-contour", action="store_true")
    actions = parser.add_subparsers(dest="action", required=True)
    status = actions.add_parser("status", allow_abbrev=False)
    status.add_argument("--session-uid", action=Once)
    status.add_argument("--full", action="store_true")
    detail = actions.add_parser("detail", allow_abbrev=False)
    detail.add_argument("--session-uid", required=True, action=Once)
    for action in ("register", "update", "leave"):
        child = actions.add_parser(action, allow_abbrev=False)
        child.add_argument("--write", required=True, action="store_true")
        if action != "register":
            child.add_argument("--session-uid", required=True, action=Once)
            child.add_argument("--expected-version", required=True, type=int, action=Once)
        if action == "register":
            child.add_argument("--parent-uid", action=Once)
        if action != "leave":
            child.add_argument("--task", required=True, action=Once)
            child.add_argument("--scope", required=True, action="append")
            child.add_argument("--activity", choices=ACTIVITIES, action=Once)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    parameters = vars(args).copy()
    parameters.pop("_seen_options", None)
    try:
        result = operate(**parameters)
    except (OSError, ValueError, subprocess.SubprocessError, RecursionError) as exc:
        print(f"FAIL: session presence: {str(exc)[:400]}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
