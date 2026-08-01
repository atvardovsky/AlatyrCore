#!/usr/bin/env python3
"""Render or check the compact operation index from the canonical catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scaffold_projection import build_operation_index, load_object, render_json


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "templates/target/.ai/assistant/operation-catalog.json"
INDEX = ROOT / "templates/target/.ai/assistant/operation-index.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the compact operation index from the canonical catalog."
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        expected = render_json(build_operation_index(load_object(CATALOG)))
        actual = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.write:
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(expected, encoding="utf-8")
        print(f"OK: rendered {INDEX.relative_to(ROOT)}")
        return 0
    if actual != expected:
        print(
            "FAIL: operation index drifted; run "
            "python3 tools/render_operation_index.py --write",
            file=sys.stderr,
        )
        return 1
    print("OK: operation index is generated from the canonical catalog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
