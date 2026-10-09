#!/usr/bin/env python3
"""Check or refresh compact change-package projections in an installed adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from change_package_contract import (
    ACTIVE_CHANGE_PACKAGE_STATUSES,
    INCIDENT_INDEX_PROJECTION_FIELDS,
    INDEX_PROJECTION_FIELDS,
    package_index_projection,
)
from target_tool_compat import assert_write_compatible


INDEX_PATH = Path(".ai/assistant/change-packages/index.json")


def _safe_record_path(target: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("change-package index record path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"change-package record path escapes target: {value}")
    unresolved = target / relative
    if unresolved.is_symlink():
        raise ValueError(f"change-package record path is a symlink: {value}")
    resolved = unresolved.resolve()
    try:
        resolved.relative_to(target)
    except ValueError as exc:
        raise ValueError(f"change-package record path escapes target: {value}") from exc
    if not resolved.is_file():
        raise ValueError(f"change-package record is unavailable: {value}")
    return resolved


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _project_entry(target: Path, entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("change-package index entries must be objects")
    record_path = _safe_record_path(target, entry.get("record"))
    record = _load_object(record_path)
    if record.get("record_kind") != "alatyr-change-package":
        raise ValueError(f"{record_path} is not an Alatyr change-package record")
    projection = package_index_projection(record)
    updated = dict(entry)
    for field in INDEX_PROJECTION_FIELDS:
        updated[field] = projection[field]
    incident = record.get("incident_continuity")
    include_incident = (
        record.get("status") in ACTIVE_CHANGE_PACKAGE_STATUSES
        or isinstance(incident, dict)
    )
    for field in INCIDENT_INDEX_PROJECTION_FIELDS:
        if include_incident:
            updated[field] = projection[field]
        else:
            updated.pop(field, None)
    return updated


def _render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def expected_outputs(target: Path) -> dict[Path, str]:
    """Return desired root and shard index bytes without mutating the target."""

    target = target.resolve()
    root_path = target / INDEX_PATH
    root = _load_object(root_path)
    if (
        root.get("schema_version") != 1
        or root.get("index_kind") != "target-change-package-index"
        or not isinstance(root.get("records"), list)
    ):
        raise ValueError(f"{INDEX_PATH} has an unsupported contract")

    shards = root.get("shards", [])
    if not isinstance(shards, list):
        raise ValueError(f"{INDEX_PATH}.shards must be a list")
    outputs: dict[Path, str] = {}
    projected_descriptors: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for descriptor in shards:
        if not isinstance(descriptor, dict):
            raise ValueError("change-package shard descriptors must be objects")
        shard_path = _safe_record_path(target, descriptor.get("path"))
        if shard_path in seen_paths:
            raise ValueError(f"duplicate change-package shard path: {shard_path}")
        seen_paths.add(shard_path)
        shard = _load_object(shard_path)
        if (
            shard.get("schema_version") != 1
            or shard.get("index_kind") != "target-change-package-index-shard"
            or not isinstance(shard.get("records"), list)
        ):
            raise ValueError(f"{shard_path} has an unsupported shard contract")
        projected_shard = dict(shard)
        projected_shard["records"] = [
            _project_entry(target, entry) for entry in shard["records"]
        ]
        rendered_shard = _render(projected_shard)
        outputs[shard_path] = rendered_shard
        projected_descriptor = dict(descriptor)
        projected_descriptor["sha256"] = hashlib.sha256(
            rendered_shard.encode("utf-8")
        ).hexdigest()
        projected_descriptor["record_count"] = len(projected_shard["records"])
        projected_descriptors.append(projected_descriptor)

    projected_root = dict(root)
    projected_root["records"] = [
        _project_entry(target, entry) for entry in root["records"]
    ]
    projected_root["shards"] = projected_descriptors
    outputs[root_path] = _render(projected_root)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--migration-staging", action="store_true")
    args = parser.parse_args()
    target = args.target.resolve()
    try:
        expected = expected_outputs(target)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    stale = [
        path
        for path, text in expected.items()
        if path.read_text(encoding="utf-8") != text
    ]
    if not args.write:
        if stale:
            for path in stale:
                print(
                    f"FAIL: stale change-package projection: {path.relative_to(target)}",
                    file=sys.stderr,
                )
            return 1
        print(f"OK: checked {len(expected)} change-package index projection(s)")
        return 0

    try:
        assert_write_compatible(
            target,
            tool_name="render_change_package_index.py",
            migration_staging=args.migration_staging,
        )
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    for path in stale:
        path.write_text(expected[path], encoding="utf-8")
    print(f"Wrote {len(stale)} stale change-package index projection(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
