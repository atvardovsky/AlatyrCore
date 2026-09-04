#!/usr/bin/env python3
"""Project canonical target templates onto one scaffold support profile."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath
from typing import Any

from scaffold_state import INITIAL_INSTALLATION_STATE

@dataclass(frozen=True)
class SelectedPathIndex:
    """Immutable exact-path and ancestor index for one target projection."""

    exact: frozenset[PurePosixPath]
    ancestors: frozenset[PurePosixPath]


SelectedPaths = Any

TARGET_PATH_RE = re.compile(
    r"^(?P<prefix>\s+[A-Za-z0-9_-]+:\s+)(?P<quote>[\"']?)(?P<path>\.ai/[^\"']+)(?P=quote)\s*$"
)
INSTALLATION_STATE_RE = re.compile(r'^(\s{2}state:\s+)["\']?[^"\']+["\']?\s*$')
MARKDOWN_FRAGMENT_OPEN_RE = re.compile(
    r"^<!-- alatyr:scaffold-fragment (?P<condition>\{.*\}) -->\s*$"
)
MARKDOWN_FRAGMENT_CLOSE = "<!-- /alatyr:scaffold-fragment -->"
MARKDOWN_FRAGMENT_INLINE_RE = re.compile(
    r"^<!-- alatyr:scaffold-fragment (?P<condition>\{.*\}) -->"
    r"(?P<content>.*)<!-- /alatyr:scaffold-fragment -->\s*$"
)
MARKDOWN_FRAGMENT_KEYS = {"requires_paths", "requires_modules"}


def portable_relative_path(value: str | PurePath) -> PurePosixPath:
    """Normalize repository-relative contract paths independently of the host OS."""

    text = value.as_posix() if isinstance(value, PurePath) else value.replace("\\", "/")
    return PurePosixPath(text)


def selected_path_index(selected: SelectedPaths) -> SelectedPathIndex:
    """Return a reusable O(1) availability index for selected paths."""

    if isinstance(selected, SelectedPathIndex):
        return selected
    exact = frozenset(portable_relative_path(candidate) for candidate in selected)
    ancestors = frozenset(parent for candidate in exact for parent in candidate.parents)
    return SelectedPathIndex(exact=exact, ancestors=ancestors)


def path_available(value: str, selected: SelectedPaths) -> bool:
    if not value.startswith(".ai/"):
        return True
    path = portable_relative_path(value)
    index = selected_path_index(selected)
    return path in index.exact or path in index.ancestors


def directory_available(value: str, selected: SelectedPaths) -> bool:
    path = portable_relative_path(value)
    index = selected_path_index(selected)
    return path in index.exact or path in index.ancestors


def project_markdown_fragments(
    text: str,
    selected: SelectedPaths,
    enabled_modules: set[str] | None = None,
) -> str:
    """Render source-readable Markdown fragments for installed support only."""

    rendered: list[str] = []
    fragment_lines: list[str] | None = None
    include_fragment = False
    modules = enabled_modules or set()

    def condition_matches(condition_text: str, line_number: int) -> bool:
        try:
            condition = json.loads(condition_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid scaffold Markdown fragment at line {line_number}: {exc.msg}"
            ) from exc
        if not isinstance(condition, dict) or not condition:
            raise ValueError(
                f"scaffold Markdown fragment at line {line_number} needs conditions"
            )
        unknown_keys = sorted(set(condition) - MARKDOWN_FRAGMENT_KEYS)
        if unknown_keys:
            raise ValueError(
                "scaffold Markdown fragment at line "
                f"{line_number} has unknown conditions: {unknown_keys}"
            )
        required_paths = condition.get("requires_paths", [])
        required_modules = condition.get("requires_modules", [])
        if not all(
            isinstance(values, list)
            and values
            and all(isinstance(value, str) and value for value in values)
            for values in [required_paths, required_modules]
            if values
        ):
            raise ValueError(
                f"scaffold Markdown fragment at line {line_number} has invalid conditions"
            )
        if not required_paths and not required_modules:
            raise ValueError(
                f"scaffold Markdown fragment at line {line_number} needs requirements"
            )
        if any(not value.startswith(".ai/") for value in required_paths):
            raise ValueError(
                f"scaffold Markdown fragment at line {line_number} has a non-.ai path"
            )
        return all(
            path_available(value, selected) for value in required_paths
        ) and set(required_modules).issubset(modules)

    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        marker = line.rstrip("\r\n")
        inline_match = MARKDOWN_FRAGMENT_INLINE_RE.match(marker)
        if inline_match:
            if fragment_lines is not None:
                raise ValueError(
                    f"nested scaffold Markdown fragment at line {line_number}"
                )
            if condition_matches(inline_match.group("condition"), line_number):
                rendered.append(inline_match.group("content") + line[len(marker) :])
            continue
        open_match = MARKDOWN_FRAGMENT_OPEN_RE.match(marker)
        if open_match:
            if fragment_lines is not None:
                raise ValueError(
                    f"nested scaffold Markdown fragment at line {line_number}"
                )
            include_fragment = condition_matches(
                open_match.group("condition"), line_number
            )
            fragment_lines = []
            continue
        if marker == MARKDOWN_FRAGMENT_CLOSE:
            if fragment_lines is None:
                raise ValueError(
                    f"unmatched scaffold Markdown fragment close at line {line_number}"
                )
            if include_fragment:
                rendered.extend(fragment_lines)
            fragment_lines = None
            include_fragment = False
            continue
        if fragment_lines is not None:
            fragment_lines.append(line)
        else:
            rendered.append(line)

    if fragment_lines is not None:
        raise ValueError("unclosed scaffold Markdown fragment")
    return "".join(rendered)


def project_manifest(
    text: str,
    profile: str,
    framework_pack: str,
    selected: SelectedPaths,
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
        if current_top_level == "installation" and INSTALLATION_STATE_RE.match(line):
            line = f'  state: "{INITIAL_INSTALLATION_STATE}"'
        if "{KERNEL_CORE_STANDARD_OR_FULL}" in line:
            line = line.replace("{KERNEL_CORE_STANDARD_OR_FULL}", profile)
        if "{CORE_STANDARD_OR_FULL}" in line:
            line = line.replace("{CORE_STANDARD_OR_FULL}", profile)
        if "{KERNEL_CORE_STANDARD_OR_COMPLETE}" in line:
            line = line.replace("{KERNEL_CORE_STANDARD_OR_COMPLETE}", framework_pack)
        if "{CORE_STANDARD_OR_COMPLETE}" in line:
            line = line.replace("{CORE_STANDARD_OR_COMPLETE}", framework_pack)
        match = TARGET_PATH_RE.match(line)
        if match and not path_available(match.group("path"), selected):
            continue
        if line == "approvals:" and not directory_available(
            ".ai/assistant/approvals", selected
        ):
            continue
        if line.strip() == '- "{ENABLED_MODULE}"' and module_items:
            rendered.extend(f'    - "{module_id}"' for module_id in module_items)
        else:
            rendered.append(line)
    return "\n".join(rendered) + "\n"


OPERATION_ROUTING_PARAGRAPH = """Route IDs/aliases through `.ai/assistant/operation-index.json`; otherwise use
profile candidates. For `Alatyr`, help, ambiguity, or repair, use
`.ai/assistant/help.md`, `.ai/assistant/operation-catalog.json`, and
`.ai/assistant/flows/operation-routing.flow.md`. Status is read-only."""

KERNEL_OPERATION_ROUTING_PARAGRAPH = """Use profile candidates from `.ai/assistant/entry-packet.json` for operation
routing. The installed operation catalog is absent in this support profile;
for `Alatyr`, help, ambiguity, or repair, use `.ai/assistant/help.md` and
report missing operation-catalog support before relying on aliases. Status is
read-only."""

AI_INFRASTRUCTURE_ROUTING_SENTENCE = (
    "Select one\n"
    "`.ai/assistant/ai-infrastructure-router.json` route and the smallest AI item\n"
    "set. Run only existing validation."
)

KERNEL_AI_INFRASTRUCTURE_ROUTING_SENTENCE = (
    "When the AI infrastructure router is installed, select one route and the\n"
    "smallest AI item set. Run only existing validation."
)

ASSISTANT_CAPABILITY_PARAGRAPH = """Before delegation or diagrams, read `.ai/assistant/assistant-capabilities.json`;
route selected delegation through its surface record and
`.ai/assistant/prompts/worker-orchestration.md`. Unknown, stale, or unverified
state means no native capability claim; unknown presentation uses ASCII."""

KERNEL_ASSISTANT_CAPABILITY_PARAGRAPH = """Before delegation or diagrams, use `.ai/assistant/entry-packet.json` and
module state. If assistant capability records or worker orchestration prompts
are absent, make no native capability claim; unknown presentation uses ASCII."""


def project_agent_rule_ids(
    text: str,
    rule_ids: list[str],
    selected: SelectedPaths | None = None,
) -> str:
    """Limit root instructions to installed rule owners and support surfaces."""

    rendered_ids = ", ".join(f"`{rule_id}`" for rule_id in rule_ids)
    pattern = re.compile(
        r"Use installed owners for .*?\. Project\nfacts belong",
        flags=re.DOTALL,
    )
    replacement = f"Use installed owners for {rendered_ids}. Project\nfacts belong"
    rendered, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError("cannot project AGENTS.md registered rule IDs")
    if selected is None:
        return rendered
    if not path_available(".ai/assistant/operation-index.json", selected):
        rendered = rendered.replace(
            OPERATION_ROUTING_PARAGRAPH,
            KERNEL_OPERATION_ROUTING_PARAGRAPH,
        )
    if not path_available(".ai/assistant/ai-infrastructure-router.json", selected):
        rendered = rendered.replace(
            AI_INFRASTRUCTURE_ROUTING_SENTENCE,
            KERNEL_AI_INFRASTRUCTURE_ROUTING_SENTENCE,
        )
    if not path_available(".ai/assistant/assistant-capabilities.json", selected):
        rendered = rendered.replace(
            ASSISTANT_CAPABILITY_PARAGRAPH,
            KERNEL_ASSISTANT_CAPABILITY_PARAGRAPH,
        )
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


def project_catalog(catalog: dict[str, Any], selected: SelectedPaths) -> dict[str, Any]:
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


def project_gate_index(gates: dict[str, Any], selected: SelectedPaths) -> dict[str, Any]:
    """Keep only gate index entries whose fragment files are installed."""

    projected = copy.deepcopy(gates)
    gate_entries = projected.get("gates")
    if not isinstance(gate_entries, dict):
        raise ValueError("gate index must define a gates object")
    available: dict[str, Any] = {}
    for gate_id, entry in gate_entries.items():
        if not isinstance(gate_id, str) or not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path_available(path, selected):
            available[gate_id] = entry
    projected["gates"] = available
    profile_defaults = projected.get("profile_defaults")
    if isinstance(profile_defaults, dict):
        projected["profile_defaults"] = {
            profile: [
                gate_id
                for gate_id in gate_ids
                if isinstance(gate_id, str) and gate_id in available
            ]
            for profile, gate_ids in profile_defaults.items()
            if isinstance(gate_ids, list)
        }
    return projected


def project_assistant_capability_index(
    capabilities: dict[str, Any], selected: SelectedPaths
) -> dict[str, Any]:
    """Keep only installed assistant records and bridge paths in the index."""

    projected = copy.deepcopy(capabilities)
    index = selected_path_index(selected)
    surfaces = projected.get("surfaces")
    bridges = projected.get("bridge_paths")
    if not isinstance(surfaces, dict) or not isinstance(bridges, dict):
        raise ValueError("assistant capability index must define surfaces and bridge_paths")
    projected_surfaces = {
        surface_id: path
        for surface_id, path in surfaces.items()
        if isinstance(surface_id, str)
        and isinstance(path, str)
        and portable_relative_path(path) in index.exact
    }
    if not projected_surfaces:
        raise ValueError("assistant capability index projection has no installed records")
    projected["surfaces"] = projected_surfaces
    projected["bridge_paths"] = {
        surface_id: [
            path
            for path in bridges.get(surface_id, [])
            if isinstance(path, str) and portable_relative_path(path) in index.exact
        ]
        for surface_id in projected_surfaces
    }
    default_surface = projected.get("default_surface")
    if default_surface not in projected_surfaces:
        projected["default_surface"] = next(iter(projected_surfaces))
    return projected


def _filter_paths(value: Any, selected: SelectedPaths) -> Any:
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


def _context_contract_available(contract: Any, selected: SelectedPaths) -> bool:
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
    selected: SelectedPaths,
    operation_ids: set[str],
) -> dict[str, Any]:
    """Remove routes and overlays that point outside the selected profile."""

    projected = copy.deepcopy(router)
    has_catalog = path_available(".ai/assistant/operation-catalog.json", selected)
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

    descriptor_routes = {
        "consistency_routing": ".ai/project/consistency-map.json",
        "migration_routing": ".ai/assistant/context/migration-routing.json",
        "project_knowledge_routing": ".ai/assistant/context/project-knowledge-routing.json",
    }
    for route, required_path in descriptor_routes.items():
        if not path_available(required_path, selected):
            projected.pop(route, None)
    return _filter_paths(projected, selected)


def project_context_descriptor(
    descriptor: dict[str, Any],
    selected: SelectedPaths,
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
    router: dict[str, Any], selected: SelectedPaths
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
