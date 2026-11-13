#!/usr/bin/env python3
"""Select bounded evidence for a read-only project question without changing files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cli_inputs import Once
from project_lookup import PURPOSES, project_lookup, render_lookup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path, action=Once)
    parser.add_argument("--question", required=True, action=Once)
    parser.add_argument("--purpose", choices=PURPOSES, default="observed-code", action=Once)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--fact-type", action=Once)
    parser.add_argument("--start-line", type=int, action=Once)
    parser.add_argument("--end-line", type=int, action=Once)
    parser.add_argument("--architecture-item", action=Once)
    parser.add_argument("--navigation-report", type=Path, action=Once)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not args.target.is_dir():
            raise ValueError("target must be an existing repository directory")
        result = project_lookup(args.target, args.question, args.source, purpose=args.purpose,
            fact_type=args.fact_type, start_line=args.start_line, end_line=args.end_line,
            architecture_item=args.architecture_item, navigation_report=args.navigation_report)
        print(render_lookup(result), end="")
    except (OSError, ValueError, RecursionError, ImportError) as exc:
        print(json.dumps({"status": "blocked", "findings": [{"code": "PROJECT_LOOKUP_INPUT", "message": str(exc)}],
                          "authorization_granted": False, "acceptance_granted": False}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
