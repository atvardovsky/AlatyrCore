#!/usr/bin/env python3
"""Project canonical target templates onto one scaffold support profile."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


TARGET_PATH_RE = re.compile(
    r"^(?P<prefix>\s+[A-Za-z0-9_-]+:\s+)(?P<quote>[\"']?)(?P<path>\.ai/[^\"']+)(?P=quote)\s*$"
)


def path_available(value: str, selected: set[Path]) -> bool:
    if not value.startswith(".ai/"):
        return True
    path = Path(value)
    return path in selected or any(path in candidate.parents for candidate in selected)


def project_manifest(
    text: str,
    profile: str,
    framework_pack: str,
    selected: set[Path],
    enabled_modules: set[str] | None = None,
) -> str:
    """Remove manifest path claims for surfaces absent from the scaffold."""

    rendered: list[str] = []
    module_items = sorted(enabled_modules or set())
    source_lines = text.splitlines()
    disabled_sections: set[str] = set()
    current_section: str | None = None
    section_contracts: set[str] = set()
    section_paths: dict[str, list[str]] = {}
    for source_line in source_lines:
        top_level = re.match(r"^([A-Za-z0-9_-]+):\s*$", source_line)
        if top_level:
            current_section = top_level.group(1)
        if current_section is None:
            continue
        if re.match(r"^\s+contract_version:\s+", source_line):
            section_contracts.add(current_section)
        path_match = TARGET_PATH_RE.match(source_line)
        if path_match:
            section_paths.setdefault(current_section, []).append(path_match.group("path"))
    for section in section_contracts:
        paths = section_paths.get(section, [])
        if paths and not any(path_available(path, selected) for path in paths):
            disabled_sections.add(section)
    current_top_level: str | None = None
    for line in source_lines:
        top_level = re.match(r"^([A-Za-z0-9_-]+):\s*$", line)
        if top_level:
            current_top_level = top_level.group(1)
        if current_top_level in disabled_sections:
            continue
        if "{CORE_STANDARD_OR_FULL}" in line:
            line = line.replace("{CORE_STANDARD_OR_FULL}", profile)
        if "{CORE_STANDARD_OR_COMPLETE}" in line:
            line = line.replace("{CORE_STANDARD_OR_COMPLETE}", framework_pack)
        match = TARGET_PATH_RE.match(line)
        if match and not path_available(match.group("path"), selected):
            continue
        if line == "approvals:" and not any(
            Path(".ai/assistant/approvals") in path.parents for path in selected
        ):
            continue
        if line.strip() == '- "{ENABLED_MODULE}"' and module_items:
            rendered.extend(f'    - "{module_id}"' for module_id in module_items)
        else:
            rendered.append(line)
    return "\n".join(rendered) + "\n"


def project_agent_rule_ids(text: str, rule_ids: list[str]) -> str:
    """Limit the root rule summary to IDs present in a selective pack."""

    rendered_ids = ", ".join(f"`{rule_id}`" for rule_id in rule_ids)
    pattern = re.compile(
        r"Use installed owners for .*?\. Project\nfacts belong",
        flags=re.DOTALL,
    )
    replacement = f"Use installed owners for {rendered_ids}. Project\nfacts belong"
    rendered, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError("cannot project AGENTS.md registered rule IDs")
    return rendered


def project_module_profile(text: str, enabled_modules: set[str]) -> str:
    """Project scaffold-selected capabilities into the human module profile."""

    rendered = text
    for module_id in sorted(enabled_modules):
        pattern = re.compile(
            rf"(^Module: `{re.escape(module_id)}`\s*$[\s\S]*?^State:\s*)"
            r"`?\{ENABLED_DEFERRED_DISABLED_NOT_APPLICABLE_OR_BLOCKED\}`?\s*$",
            flags=re.MULTILINE,
        )
        rendered, count = pattern.subn(r"\1`enabled`", rendered, count=1)
        if count != 1:
            raise ValueError(f"cannot project enabled module {module_id} into module profile")
    return rendered


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def project_catalog(catalog: dict[str, Any], selected: set[Path]) -> dict[str, Any]:
    """Keep only operations whose flow and catalog support files are installed."""

    projected = copy.deepcopy(catalog)
    operations = projected.get("operations")
    if not isinstance(operations, list):
        raise ValueError("operation catalog must define an operations list")
    projected["operations"] = [
        operation
        for operation in operations
        if isinstance(operation, dict)
        and isinstance(operation.get("flow"), str)
        and path_available(operation["flow"], selected)
    ]
    return projected


def build_operation_index(catalog: dict[str, Any]) -> dict[str, Any]:
    """Derive the compact exact-alias index from a canonical catalog."""

    aliases: dict[str, str] = {}
    operations: dict[str, list[str]] = {}
    for operation in catalog.get("operations", []):
        if not isinstance(operation, dict):
            continue
        operation_id = operation.get("id")
        module = operation.get("required_module")
        flow = operation.get("flow")
        actions = operation.get("allowed_actions")
        if not all(isinstance(value, str) and value for value in [operation_id, module, flow]):
            continue
        if not isinstance(actions, list) or not all(isinstance(value, str) for value in actions):
            continue
        for alias in operation.get("aliases", []):
            if isinstance(alias, str) and alias:
                aliases[alias] = operation_id
        operations[operation_id] = [module, flow, *actions]
    return {
        "schema_version": 1,
        "index_kind": "target-operation-index",
        "catalog": ".ai/assistant/operation-catalog.json",
        "aliases": aliases,
        "operations": operations,
    }


def _filter_paths(value: Any, selected: set[Path]) -> Any:
    if isinstance(value, list):
        return [
            _filter_paths(item, selected)
            for item in value
            if (
                (not isinstance(item, str) or path_available(item, selected))
                and (
                    not isinstance(item, dict)
                    or not isinstance(item.get("path"), str)
                    or path_available(item["path"], selected)
                )
            )
        ]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, str) and not path_available(item, selected):
                continue
            result[key] = _filter_paths(item, selected)
        return result
    return value


def _context_contract_available(contract: Any, selected: set[Path]) -> bool:
    if not isinstance(contract, dict):
        return False
    references = contract.get("required_context", [])
    if not isinstance(references, list):
        return False
    return all(
        not isinstance(reference, str) or path_available(reference, selected)
        for reference in references
    )


def project_router(
    router: dict[str, Any],
    selected: set[Path],
    operation_ids: set[str],
) -> dict[str, Any]:
    """Remove routes and overlays that point outside the selected profile."""

    projected = copy.deepcopy(router)
    has_catalog = Path(".ai/assistant/operation-catalog.json") in selected
    if not has_catalog:
        projected.pop("operation_routing", None)

    profiles = projected.get("profile_index")
    if isinstance(profiles, dict):
        available_profiles: dict[str, Any] = {}
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            descriptor = profile.get("descriptor")
            if not isinstance(descriptor, str) or not path_available(
                descriptor, selected
            ):
                continue
            candidates = profile.get("operation_candidates")
            if isinstance(candidates, list):
                if has_catalog:
                    profile["operation_candidates"] = [
                        value for value in candidates if value in operation_ids
                    ]
                else:
                    profile.pop("operation_candidates", None)
            available_profiles[name] = profile
        projected["profile_index"] = available_profiles
        order = projected.get("routing_order")
        if isinstance(order, list):
            projected["routing_order"] = [
                value for value in order if value in available_profiles
            ]

    overlays = projected.get("intent_overlays")
    if isinstance(overlays, dict):
        projected["intent_overlays"] = {
            name: overlay
            for name, overlay in overlays.items()
            if _context_contract_available(overlay, selected)
            and isinstance(overlay.get("operation_candidates"), list)
            and all(value in operation_ids for value in overlay["operation_candidates"])
        }

    scale_overlays = projected.get("task_scale_overlays")
    if isinstance(scale_overlays, dict):
        projected["task_scale_overlays"] = {
            name: overlay
            for name, overlay in scale_overlays.items()
            if _context_contract_available(overlay, selected)
            and (
                not isinstance(overlay.get("descriptor"), str)
                or path_available(overlay["descriptor"], selected)
            )
        }

    if not path_available(".ai/project/consistency-map.json", selected):
        projected.pop("consistency_routing", None)
    return _filter_paths(projected, selected)


def project_context_descriptor(
    descriptor: dict[str, Any],
    selected: set[Path],
    operation_ids: set[str],
) -> dict[str, Any]:
    """Project one lazy context descriptor onto installed paths and operations."""

    projected = copy.deepcopy(descriptor)
    candidates = projected.get("operation_candidates")
    if isinstance(candidates, list):
        if operation_ids:
            projected["operation_candidates"] = [
                value for value in candidates if value in operation_ids
            ]
        else:
            projected.pop("operation_candidates", None)
    return _filter_paths(projected, selected)


def project_ai_infrastructure_router(
    router: dict[str, Any], selected: set[Path]
) -> dict[str, Any]:
    """Remove routes whose concrete canonical context is not installed."""

    projected = copy.deepcopy(router)
    routes = projected.get("routes")
    if not isinstance(routes, dict):
        return projected
    available_routes: dict[str, Any] = {}
    for name, route in routes.items():
        if not isinstance(route, dict):
            continue
        required = route.get("required_context", [])
        if not isinstance(required, list):
            continue
        concrete = [
            value
            for value in required
            if isinstance(value, str) and value.startswith(".ai/")
        ]
        if all(path_available(value, selected) for value in concrete):
            available_routes[name] = _filter_paths(route, selected)
    projected["routes"] = available_routes
    order = projected.get("routing_order")
    if isinstance(order, list):
        projected["routing_order"] = [
            value for value in order if value in available_routes
        ]
    return projected


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"
