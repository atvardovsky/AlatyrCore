#!/usr/bin/env python3
"""Render or check the assistant capability index from per-surface records."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from target_adapter_validation.assistant_capabilities import (
    CAPABILITY_INDEX_KIND,
    CAPABILITY_INDEX_SCHEMA_VERSION,
    capability_record_path,
    expected_index_state_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates/target/.ai/assistant"
INDEX = TARGET / "assistant-capabilities.json"
SURFACES = ROOT / "conformance/runs/assistant-surfaces.json"
RECORDS = TARGET / "assistant-capabilities"


def load_object(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def surface_ids() -> list[str]:
    values = load_object(SURFACES).get("surfaces")
    if not isinstance(values, list):
        raise ValueError("assistant surfaces must be a list")
    ids = [item.get("id") if isinstance(item, dict) else None for item in values]
    if not all(isinstance(surface_id, str) and surface_id for surface_id in ids):
        raise ValueError("assistant surface has no valid ID")
    return sorted(ids)


def build_surface_record(surface_id: str) -> dict[str, object]:
    template = load_object(RECORDS / "generic.json")
    record = copy.deepcopy(template)
    record["assistant_surface"] = surface_id
    return record


def write_surface_records() -> int:
    written = 0
    for surface_id in surface_ids():
        path = RECORDS / f"{surface_id}.json"
        expected = json.dumps(build_surface_record(surface_id), indent=2) + "\n"
        actual = path.read_text(encoding="utf-8") if path.is_file() else ""
        if actual != expected:
            path.write_text(expected, encoding="utf-8")
            written += 1
    return written


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
        relpath = capability_record_path(surface_id)
        record = load_object(ROOT / "templates/target" / relpath)
        if record.get("assistant_surface") != surface_id:
            raise ValueError(f"capability record identity differs for {surface_id}")
        surface_paths[surface_id] = relpath
        bridge_paths[surface_id] = surface_bridge_paths
    return {
        "schema_version": CAPABILITY_INDEX_SCHEMA_VERSION,
        "capability_kind": CAPABILITY_INDEX_KIND,
        "human_reference": ".ai/assistant/bridge-capability-matrix.md",
        "default_surface": "generic",
        "state_evidence": expected_index_state_evidence(),
        "surfaces": surface_paths,
        "bridge_paths": bridge_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the assistant capability index from surface records."
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--write-records",
        action="store_true",
        help="Regenerate every surface record from generic.json before the index.",
    )
    args = parser.parse_args()
    try:
        written_records = write_surface_records() if args.write_records else 0
        expected = json.dumps(build_index(), indent=2) + "\n"
        actual = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.write:
        INDEX.write_text(expected, encoding="utf-8")
        print(
            f"OK: rendered {INDEX.relative_to(ROOT)}; "
            f"surface_records_updated={written_records}"
        )
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
