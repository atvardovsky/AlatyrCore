#!/usr/bin/env python3
"""Inspect explicit Python source bindings and dependency review candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from code_relationships import inspect_relationships, render_relationship_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--map", default=".ai/project/consistency-map.json")
    args = parser.parse_args()
    try:
        result = inspect_relationships(args.target, args.source, source_root=args.source_root, map_path=args.map)
        rendered = render_relationship_report(result)
    except (OSError, ValueError, SyntaxError, RecursionError) as exc:
        print(json.dumps({"status": "blocked", "findings": [{"code": "CODE_RELATIONSHIP_INPUT", "message": str(exc)}]}))
        return 1
    sys.stdout.buffer.write(rendered.encode("utf-8"))
    return int(bool(result["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
