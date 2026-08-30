"""Build the compact installed-adapter first-use routing packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


PACKET_PATH = Path(".ai/assistant/entry-packet.json")
SOURCE_PATHS = {
    "manifest": Path(".ai/alatyr.yaml"),
    "context_router": Path(".ai/assistant/context-router.json"),
    "gate_index": Path(".ai/assistant/gates/index.json"),
    "action_authorization_policy": Path(
        ".ai/assistant/policies/action-authorization.json"
    ),
    "support_policy": Path(".ai/project/support-policy.json"),
}
OPTIONAL_SOURCE_PATHS = {
    "operation_index": Path(".ai/assistant/operation-index.json"),
    "operation_catalog": Path(".ai/assistant/operation-catalog.json"),
}

ALLOWED_ACTION_MODES = {
    "read-only": "inspect analyze discuss review plan explain compare or report without file or external-state changes",
    "docs-only": "change documentation blueprint diagram source or support explanation only; do not change product code",
    "adapter-only": "change Alatyr adapter, assistant bridge, prompt, gate, or template surfaces only",
    "code-and-tests": "change product code and tests with synchronized docs as needed; no publish or live-external action",
    "full-with-approval": "perform protected or broad state-changing work only within explicit current approval scope",
}

LAZY_HEAVY_SURFACES = [
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/assistant/help-reference.md",
    ".ai/support-state.json",
]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _string(value: Any, default: str = "unknown") -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_optional_text(target: Path, path: Path) -> str | None:
    source = target / path
    if not source.is_file():
        return None
    return source.read_text(encoding="utf-8")


def _load_json_text(text: str, label: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _load_yaml_text(text: str, label: str) -> dict[str, Any]:
    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a YAML mapping")
    return value


def _derived_from(
    source_texts: dict[str, str], optional_source_texts: dict[str, str]
) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for name, path in SOURCE_PATHS.items():
        entries[name] = {"path": path.as_posix(), "sha256": _sha256(source_texts[name])}
    for name, text in optional_source_texts.items():
        entries[name] = {
            "path": OPTIONAL_SOURCE_PATHS[name].as_posix(),
            "sha256": _sha256(text),
        }
    return entries


def _gate_paths(gates: dict[str, Any], gate_ids: list[str]) -> list[str]:
    gate_index = _object(gates.get("gates"))
    paths: list[str] = []
    for gate_id in gate_ids:
        entry = _object(gate_index.get(gate_id))
        path = entry.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return paths


def _operation_routes(operation_index: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if operation_index is None:
        return {}
    operations = _object(operation_index.get("operations"))
    routes: dict[str, dict[str, Any]] = {}
    for operation_id, route in operations.items():
        if not isinstance(operation_id, str) or not isinstance(route, list):
            continue
        values = [item for item in route if isinstance(item, str) and item]
        if len(values) < 2:
            continue
        routes[operation_id] = {
            "required_module": values[0],
            "flow": values[1],
            "allowed_actions": values[2:],
        }
    return routes


def _profile_routes(
    router: dict[str, Any],
    gates: dict[str, Any],
    target: Path | None,
    profile_descriptors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    profiles = _object(router.get("profile_index"))
    defaults = _object(gates.get("profile_defaults"))
    routes: dict[str, dict[str, Any]] = {}
    for profile_id, entry in profiles.items():
        if not isinstance(profile_id, str) or not isinstance(entry, dict):
            continue
        descriptor = entry.get("descriptor")
        descriptor_data: dict[str, Any] = (profile_descriptors or {}).get(
            profile_id,
            {},
        )
        if not descriptor_data and isinstance(descriptor, str) and target is not None:
            descriptor_path = target / descriptor
            if descriptor_path.is_file():
                descriptor_data = _load_json_text(
                    descriptor_path.read_text(encoding="utf-8"),
                    descriptor,
                )
        default_gate_ids = _string_list(defaults.get(profile_id))
        routes[profile_id] = {
            "signals": _string_list(entry.get("use_when")),
            "descriptor": _string(descriptor),
            "operations": _string_list(
                descriptor_data.get("operation_candidates")
                or entry.get("operation_candidates")
            ),
            "required_context": _string_list(descriptor_data.get("required_context")),
            "default_gates": default_gate_ids,
            "default_gate_paths": _gate_paths(gates, default_gate_ids),
            "approval_gates": _string_list(descriptor_data.get("approval_gates")),
            "validation": _string_list(descriptor_data.get("validation")),
            "final_evidence": _string_list(descriptor_data.get("final_evidence")),
        }
    return routes


def build_agent_entry_packet(
    manifest_text: str,
    router_text: str,
    gate_index_text: str,
    action_authorization_text: str,
    support_policy_text: str,
    *,
    operation_index_text: str | None = None,
    operation_catalog_text: str | None = None,
    target: Path | None = None,
    profile_descriptors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic compact routing packet from target sources."""

    manifest = _load_yaml_text(manifest_text, ".ai/alatyr.yaml")
    router = _load_json_text(router_text, ".ai/assistant/context-router.json")
    gates = _load_json_text(gate_index_text, ".ai/assistant/gates/index.json")
    authorization = _load_json_text(
        action_authorization_text,
        ".ai/assistant/policies/action-authorization.json",
    )
    support_policy = _load_json_text(
        support_policy_text,
        ".ai/project/support-policy.json",
    )
    operation_index = (
        _load_json_text(operation_index_text, ".ai/assistant/operation-index.json")
        if operation_index_text is not None
        else None
    )

    framework = _object(manifest.get("framework"))
    installation = _object(manifest.get("installation"))
    modules = _object(manifest.get("modules"))
    context_budgets = _object(router.get("context_budgets"))
    operation_routing = _object(router.get("operation_routing"))
    optional_texts = {
        name: text
        for name, text in {
            "operation_index": operation_index_text,
            "operation_catalog": operation_catalog_text,
        }.items()
        if text is not None
    }

    return {
        "schema_version": 1,
        "packet_kind": "target-agent-entry-packet",
        "path": PACKET_PATH.as_posix(),
        "derived_from": _derived_from(
            {
                "manifest": manifest_text,
                "context_router": router_text,
                "gate_index": gate_index_text,
                "action_authorization_policy": action_authorization_text,
                "support_policy": support_policy_text,
            },
            optional_texts,
        ),
        "installation": {
            "framework_version": _string(framework.get("version")),
            "adapter_schema_version": _string(manifest.get("schema_version")),
            "template_version": _string(framework.get("template_version")),
            "support_profile": _string(installation.get("support_profile")),
            "framework_pack": _string(framework.get("pack")),
            "installation_state": _string(installation.get("state")),
            "enabled_modules": _string_list(modules.get("enabled")),
        },
        "entry_sequence": [
            {
                "phase": "host-preloaded",
                "paths": _string_list(router.get("preloaded_context")),
            },
            {
                "phase": "bootstrap",
                "paths": _string_list(router.get("bootstrap_context")),
            },
            {
                "phase": "first-use-packet",
                "paths": [PACKET_PATH.as_posix()],
            },
        ],
        "budget_summary": {
            "bootstrap": _object(context_budgets.get("bootstrap")),
            "profile_default": _object(context_budgets.get("profile_default")),
            "on_exceed": _string(context_budgets.get("on_exceed")),
        },
        "profile_recommendation": {
            "default_install_profile": "kernel",
            "escalation_order": ["kernel", "core", "standard", "full"],
            "select_core_when": [
                "durable engineering evidence or project knowledge is needed",
                "optional capability dependency closure requires core or broader",
            ],
            "select_standard_when": [
                "common lifecycle, product-change, operation catalog, or post-update operations are required",
            ],
            "select_full_when": [
                "native assistant bridges, all optional support templates, or full-profile conformance are explicitly required",
            ],
            "decision_policy": "install or update the cheapest sufficient profile from target evidence; escalate only for a named missing surface, module dependency, assistant bridge, or failed validation",
        },
        "profile_routes": _profile_routes(
            router,
            gates,
            target,
            profile_descriptors,
        ),
        "operation_routing": {
            "index": _string(operation_routing.get("index"), "not installed"),
            "catalog": _string(operation_routing.get("catalog"), "not installed"),
            "fallback_operation": _string(
                operation_routing.get("fallback_operation"),
                "help",
            ),
            "load_index_when": _string_list(operation_routing.get("load_index_when")),
            "load_catalog_when": _string_list(operation_routing.get("load_catalog_when")),
            "operation_routes": _operation_routes(operation_index),
        },
        "authorization": {
            "policy": SOURCE_PATHS["action_authorization_policy"].as_posix(),
            "default_phase": _string(authorization.get("default_phase"), "inspect"),
            "phases": _string_list(authorization.get("phases")),
            "allowed_action_modes": ALLOWED_ACTION_MODES,
            "current_scope_required_for": [
                "modify",
                "commit",
                "publish",
                "live-external",
            ],
        },
        "support_delta_first": {
            "policy": SOURCE_PATHS["support_policy"].as_posix(),
            "state": ".ai/support-state.json",
            "support_diff_tool": "tools/report_support_diff.py --target <target-repo>",
            "support_delta_tool": (
                "tools/report_support_delta.py --target <target-repo> "
                "--diff-ref <base-ref>"
            ),
            "impact_plan_tool": (
                "tools/plan_support_impact.py --target <target-repo> "
                "--diff-ref <base-ref>"
            ),
            "routing_policy": (
                "compare support-state hashes and Git changed paths first, "
                "then load only selected support owners, relationship shards, "
                "or target source owners; hashes locate change and never prove "
                "semantic correctness"
            ),
            "review_after_code_change": "rerun delta/impact routing for changed code paths before final evidence when support information may need sync",
            "fallback_when_missing_state": "repair or regenerate support-state with explicit adapter-write authorization before trusting broad support claims",
        },
        "lazy_human_fallbacks": LAZY_HEAVY_SURFACES,
        "reasoning_boundary": (
            "This packet selects bounded files, gates, operations, and "
            "allowed-action ceilings. Logical integrity, invariant derivation, "
            "and final correctness still require assistant and human reasoning."
        ),
    }


def build_from_target(target: Path) -> dict[str, Any]:
    target = target.resolve()
    source_texts = {
        name: (target / path).read_text(encoding="utf-8")
        for name, path in SOURCE_PATHS.items()
    }
    optional_texts = {
        name: text
        for name, path in OPTIONAL_SOURCE_PATHS.items()
        for text in [_load_optional_text(target, path)]
        if text is not None
    }
    return build_agent_entry_packet(
        source_texts["manifest"],
        source_texts["context_router"],
        source_texts["gate_index"],
        source_texts["action_authorization_policy"],
        source_texts["support_policy"],
        operation_index_text=optional_texts.get("operation_index"),
        operation_catalog_text=optional_texts.get("operation_catalog"),
        target=target,
    )


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"
