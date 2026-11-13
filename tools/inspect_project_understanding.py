#!/usr/bin/env python3
"""Prepare a cold-start understanding request or check an externally captured result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_understanding import SCENARIOS, understanding_request, check_understanding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, default="project-understanding")
    args = parser.parse_args()
    try:
        if not args.target.is_dir():
            raise ValueError("target must be an existing repository directory")
        result = (understanding_request(args.scenario) if args.report is None
                  else check_understanding(args.target, args.report, args.scenario))
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"status": "blocked", "findings": [{"code": "PROJECT_UNDERSTANDING_INPUT", "message": str(exc)}]}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
