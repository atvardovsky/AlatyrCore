#!/usr/bin/env python3
"""Validate diagram-discussion result contracts and captured assistant runs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "conformance/operations/diagram-discussion-result-template.json"
SURFACES = ROOT / "conformance/runs/assistant-surfaces.json"
DEFAULT_RESULTS = ROOT / "conformance/runs/diagram-results"
PLACEHOLDER = re.compile(r"\{[A-Z0-9_]+\}")
PRESENTATION_MODES = {"native-inline", "rendered-artifact", "text-fallback"}


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def surface_ids() -> set[str]:
    values = load_object(SURFACES).get("surfaces")
    if not isinstance(values, list):
        raise ValueError("assistant surfaces must be a list")
    result = {
        item["id"]
        for item in values
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(result) != len(values):
        raise ValueError("assistant surface IDs must be unique strings")
    return result


def require_string(data: dict[str, Any], field: str, path: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} field {field} must be a non-empty string")
    return value


def require_string_list(data: dict[str, Any], field: str, path: Path) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{path} field {field} must be a non-empty string list")
    return value


def measured_value(value: Any, field: str, path: Path) -> None:
    if isinstance(value, int) and value >= 0:
        return
    if isinstance(value, str) and value.startswith("unknown:"):
        return
    raise ValueError(f"{path} {field} must be non-negative or unknown: reason")


def validate_result(path: Path, known_surfaces: set[str], *, template: bool) -> str:
    data = load_object(path)
    if data.get("schema_version") != 1:
        raise ValueError(f"{path} schema_version must be 1")
    if data.get("report_kind") != "assistant-operation-result":
        raise ValueError(f"{path} report_kind is invalid")
    if data.get("operation") != "diagram-discussion":
        raise ValueError(f"{path} operation must be diagram-discussion")
    surface = require_string(data, "assistant_surface", path)
    if not template and surface not in known_surfaces:
        raise ValueError(f"{path} assistant_surface is unknown: {surface}")
    for field in [
        "run_id",
        "target_revision",
        "client_version",
        "captured_at",
        "diagram_id",
        "draft_revision",
        "capability_evidence",
        "data_classification",
        "text_fallback",
        "stale_view_risk",
    ]:
        require_string(data, field, path)
    if data.get("status") != "draft":
        raise ValueError(f"{path} read-only diagram status must be draft")
    mode = require_string(data, "presentation_mode", path)
    if not template and mode not in PRESENTATION_MODES:
        raise ValueError(f"{path} presentation_mode is invalid")
    if data.get("allowed_actions") != ["read-only"]:
        raise ValueError(f"{path} allowed_actions must be read-only")
    if data.get("repository_changes") != []:
        raise ValueError(f"{path} read-only result must have no repository changes")
    require_string_list(data, "validation", path)
    require_string_list(data, "residual_risk", path)

    context = data.get("loaded_context")
    if not isinstance(context, dict):
        raise ValueError(f"{path} loaded_context must be an object")
    require_string(context, "measurement_kind", path)
    loaded_paths = require_string_list(context, "loaded_paths", path)
    require_string_list(context, "loaded_sections", path)
    require_string(context, "hidden_client_context", path)
    if not template:
        required_paths = {
            ".ai/assistant/operation-index.json",
            ".ai/assistant/context/intents/diagram-request.json",
            ".ai/assistant/assistant-capabilities.json",
            f".ai/assistant/assistant-capabilities/{surface}.json",
        }
        missing = sorted(required_paths - set(loaded_paths))
        if missing:
            raise ValueError(f"{path} loaded_context is missing {missing}")
    for field in ["observed_bytes", "estimated_tokens"]:
        if not template:
            measured_value(context.get(field), field, path)
    for field in ["soft_budget_exceeded", "hard_budget_exceeded"]:
        value = context.get(field)
        if not template and not (
            isinstance(value, bool)
            or isinstance(value, str) and value.startswith("unknown:")
        ):
            raise ValueError(f"{path} {field} must be boolean or unknown: reason")

    rendered = json.dumps(data)
    if not template and PLACEHOLDER.search(rendered):
        raise ValueError(f"{path} contains unresolved placeholders")
    return surface


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate diagram operation result contracts or captured runs."
    )
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--require-all-surfaces", action="store_true")
    args = parser.parse_args()
    failures: list[str] = []
    captured: set[str] = set()
    try:
        known = surface_ids()
        validate_result(TEMPLATE, known, template=True)
        if args.results_dir:
            results_dir = args.results_dir.resolve()
            for path in sorted(results_dir.rglob("*.json")):
                captured.add(validate_result(path, known, template=False))
            if args.require_all_surfaces:
                missing = sorted(known - captured)
                if missing:
                    raise ValueError(f"captured diagram results missing surfaces: {missing}")
        elif args.require_all_surfaces:
            raise ValueError("--require-all-surfaces requires --results-dir")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked diagram result contract"
        + (f" and {len(captured)} captured surface result(s)" if args.results_dir else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
