#!/usr/bin/env python3
"""Validate target assistant capability templates and their evidence contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SURFACES = ROOT / "conformance" / "runs" / "assistant-surfaces.json"
CAPABILITIES = ROOT / "templates" / "target" / ".ai" / "assistant" / "assistant-capabilities"
SCHEMA = ROOT / "schemas" / "alatyr-assistant-surface-capability.schema.json"
EVIDENCE_FIELDS = {"verified_at", "client_version", "evidence", "expires_at", "review_triggers"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def main() -> int:
    failures: list[str] = []
    try:
        surface_data = load_object(SURFACES)
        schema = load_object(SCHEMA)
        jsonschema.Draft7Validator.check_schema(schema)
        validator = jsonschema.Draft7Validator(schema)
        raw_surfaces = surface_data.get("surfaces")
        if not isinstance(raw_surfaces, list):
            raise ValueError("assistant surfaces must be a list")
        surface_ids = {
            item.get("id")
            for item in raw_surfaces
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        records = {path.stem: path for path in CAPABILITIES.glob("*.json")}
        if set(records) != surface_ids:
            failures.append(
                "assistant capability records differ from surfaces: "
                f"missing={sorted(surface_ids - set(records))} "
                f"extra={sorted(set(records) - surface_ids)}"
            )
        for surface_id, path in sorted(records.items()):
            record = load_object(path)
            errors = sorted(
                validator.iter_errors(record),
                key=lambda error: list(error.absolute_path),
            )
            failures.extend(
                f"{path.relative_to(ROOT)} "
                + (".".join(str(item) for item in error.absolute_path) or "root")
                + f": {error.message}"
                for error in errors
            )
            if record.get("assistant_surface") != surface_id:
                failures.append(f"{surface_id} capability identity differs from filename")
            for section_name in ["instruction_loading", "skills", "tool_permissions"]:
                section = record.get(section_name)
                if not isinstance(section, dict):
                    continue
                if not EVIDENCE_FIELDS.issubset(section):
                    failures.append(f"{surface_id} {section_name} lacks evidence lifecycle")
            permissions = record.get("tool_permissions")
            if not isinstance(permissions, dict) or permissions.get(
                "alatyr_authorization_separate"
            ) is not True:
                failures.append(
                    f"{surface_id} client permissions must remain separate from Alatyr authorization"
                )
    except (OSError, ValueError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: checked instruction, skill, permission, diagram, and delegation evidence for {len(records)} assistant surfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
