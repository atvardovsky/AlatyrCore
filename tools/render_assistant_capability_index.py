#!/usr/bin/env python3
"""Render or check the assistant capability index from per-surface records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates/target/.ai/assistant"
INDEX = TARGET / "assistant-capabilities.json"
SURFACES = ROOT / "conformance/runs/assistant-surfaces.json"


def load_object(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def build_index() -> dict[str, object]:
    surface_data = load_object(SURFACES).get("surfaces")
    if not isinstance(surface_data, list):
        raise ValueError("assistant surfaces must be a list")
    surface_paths: dict[str, str] = {}
    bridge_paths: dict[str, list[str]] = {}
    for item in surface_data:
        surface_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(surface_id, str) or not surface_id:
            raise ValueError("assistant surface has no valid ID")
        surface_bridge_paths = item.get("bridge_paths")
        if not isinstance(surface_bridge_paths, list) or not all(
            isinstance(path, str) and path for path in surface_bridge_paths
        ):
            raise ValueError(f"assistant surface {surface_id} has no valid bridge paths")
        relpath = f".ai/assistant/assistant-capabilities/{surface_id}.json"
        record = load_object(ROOT / "templates/target" / relpath)
        if record.get("assistant_surface") != surface_id:
            raise ValueError(f"capability record identity differs for {surface_id}")
        surface_paths[surface_id] = relpath
        bridge_paths[surface_id] = surface_bridge_paths
    return {
        "schema_version": 3,
        "capability_kind": "target-assistant-capability-index",
        "human_reference": ".ai/assistant/bridge-capability-matrix.md",
        "default_surface": "generic",
        "state_evidence": {
            "state_model": "supported|limited|unsupported|unknown plus selected and freshness evidence",
            "selected_surface": "{TARGET_SELECTED_ASSISTANT_SURFACE_OR_GENERIC}",
            "selected_surface_evidence": "{TARGET_SELECTED_SURFACE_EVIDENCE_OR_UNKNOWN}",
            "capability_records_are_authoritative": True,
            "unknown_means_not_verified": True,
            "stale_or_expired_evidence_requires_recheck": True,
        },
        "surfaces": surface_paths,
        "bridge_paths": bridge_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the assistant capability index from surface records."
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        expected = json.dumps(build_index(), indent=2) + "\n"
        actual = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.write:
        INDEX.write_text(expected, encoding="utf-8")
        print(f"OK: rendered {INDEX.relative_to(ROOT)}")
        return 0
    if actual != expected:
        print(
            "FAIL: assistant capability index drifted; run "
            "python3 tools/render_assistant_capability_index.py --write",
            file=sys.stderr,
        )
        return 1
    print("OK: assistant capability index is generated from surface records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
