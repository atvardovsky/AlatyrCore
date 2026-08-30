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
CAPABILITY_INDEX = ROOT / "templates" / "target" / ".ai" / "assistant" / "assistant-capabilities.json"
SCHEMA = ROOT / "schemas" / "alatyr-assistant-surface-capability.schema.json"
EVIDENCE_FIELDS = {"verified_at", "client_version", "evidence", "expires_at", "review_triggers"}
STATE_FIELDS = {
    "overall",
    "selected_for_target",
    "evidence_state",
    "advertised_by_surface",
    "verified_for_target",
    "limitations",
    "review_triggers",
}


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
        records = {
            path.stem: path
            for path in CAPABILITIES.glob("*.json")
            if path.name != "context-index.json"
        }
        if set(records) != surface_ids:
            failures.append(
                "assistant capability records differ from surfaces: "
                f"missing={sorted(surface_ids - set(records))} "
                f"extra={sorted(set(records) - surface_ids)}"
            )
        capability_index = load_object(CAPABILITY_INDEX)
        if capability_index.get("schema_version") != 3:
            failures.append("assistant capability index schema_version must be 3")
        state_evidence = capability_index.get("state_evidence")
        if not isinstance(state_evidence, dict):
            failures.append("assistant capability index lacks state_evidence")
        else:
            for field in [
                "state_model",
                "selected_surface",
                "selected_surface_evidence",
            ]:
                value = state_evidence.get(field)
                if not isinstance(value, str) or not value.strip():
                    failures.append(
                        f"assistant capability index state_evidence.{field} is missing"
                    )
            for field in [
                "capability_records_are_authoritative",
                "unknown_means_not_verified",
                "stale_or_expired_evidence_requires_recheck",
            ]:
                if state_evidence.get(field) is not True:
                    failures.append(
                        f"assistant capability index state_evidence.{field} must be true"
                    )
        index_surfaces = capability_index.get("surfaces")
        if not isinstance(index_surfaces, dict) or set(index_surfaces) != surface_ids:
            failures.append("assistant capability index must cover every surface")
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
            surface_state = record.get("surface_state")
            if not isinstance(surface_state, dict):
                failures.append(f"{surface_id} capability lacks surface_state")
            else:
                missing = sorted(STATE_FIELDS - set(surface_state))
                if missing:
                    failures.append(f"{surface_id} surface_state is missing {missing}")
                for field in [
                    "overall",
                    "selected_for_target",
                    "evidence_state",
                    "advertised_by_surface",
                    "verified_for_target",
                ]:
                    value = surface_state.get(field)
                    if not isinstance(value, str) or "{" not in value:
                        failures.append(
                            f"{surface_id} surface_state.{field} must remain placeholder-based"
                        )
                for field in ["limitations", "review_triggers"]:
                    value = surface_state.get(field)
                    if not isinstance(value, list) or not value:
                        failures.append(
                            f"{surface_id} surface_state.{field} must be a non-empty list"
                        )
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
    print(
        "OK: checked assistant surface state plus instruction, skill, "
        f"permission, diagram, and delegation evidence for {len(records)} surfaces"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
