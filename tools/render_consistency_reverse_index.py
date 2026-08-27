#!/usr/bin/env python3
"""Check or regenerate the target consistency reverse index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from impact_graph import ImpactGraphError, build_reverse_index, load_impact_graph, render_json


DEFAULT_OUTPUT = ".ai/assistant/consistency-reverse-index.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        graph = load_impact_graph(target)
        expected = build_reverse_index(graph)
    except ImpactGraphError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    output_relpath = graph.root.get("reverse_index", DEFAULT_OUTPUT)
    if not isinstance(output_relpath, str):
        output_relpath = DEFAULT_OUTPUT
    output = target / output_relpath
    rendered = render_json(expected)
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(rendered.encode("utf-8"))
        print(f"Wrote {output_relpath} for {len(graph.nodes)} nodes")
        return 0
    try:
        actual = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load {output_relpath}: {exc}", file=sys.stderr)
        return 1
    if actual != expected:
        print(f"FAIL: stale {output_relpath}", file=sys.stderr)
        return 1
    print(f"OK: consistency reverse index covers {len(graph.nodes)} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
