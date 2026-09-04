"""Build the compact installed-adapter first-use routing packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from target_tool_compat import generation_provenance


PACKET_PATH = Path(".ai/assistant/entry-packet.json")
SOURCE_PATHS = {
    "manifest": Path(".ai/alatyr.yaml"),
    "context_router": Path(".ai/assistant/context-router.json"),
    "gate_index": Path(".ai/assistant/gates/index.json"),
    "action_authorization_policy": Path(
        ".ai/assistant/policies/action-authorization.json"
    ),
    "support_policy": Path(".ai/project/support-policy.json"),
    "task_decomposition": Path(".ai/assistant/task-decomposition.json"),
}
OPTIONAL_SOURCE_PATHS = {
    "operation_index": Path(".ai/assistant/operation-index.json"),
    "operation_catalog": Path(".ai/assistant/operation-catalog.json"),
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


def _task_classification(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    classes = source.get("classes")
    projected_classes: dict[str, dict[str, Any]] = {}
    if isinstance(classes, dict):
        for class_id, class_data in classes.items():
            if not isinstance(class_id, str) or not isinstance(class_data, dict):
                continue
            item: dict[str, Any] = {}
            signals = _string_list(class_data.get("use_when"))
            if signals:
                item["signals"] = signals
            overlay = class_data.get("task_scale_overlay")
            if isinstance(overlay, str) and overlay:
                item["task_scale_overlay"] = overlay
            preview = class_data.get("pre_change_preview")
            if isinstance(preview, str) and preview:
                item["pre_change_preview"] = preview
            evidence = class_data.get("evidence")
            if isinstance(evidence, str) and evidence:
                item["evidence"] = evidence
            if item:
                projected_classes[class_id] = item
    return {
        "schema_version": source.get("schema_version", "unknown"),
        "classification_order": _string_list(source.get("classification_order")),
        "default_class": _string(source.get("default_class")),
        "ambiguity_behavior": _string(source.get("ambiguity_behavior")),
        "classes": projected_classes,
        "expansion_triggers": _string_list(source.get("expansion_triggers")),
    }


def _task_decomposition_summary(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    levels = source.get("levels")
    level_order: list[str] = []
    non_delegable_levels: list[str] = []
    worker_eligible_levels: list[str] = []
    if isinstance(levels, list):
        for level in levels:
            if not isinstance(level, dict):
                continue
            level_id = level.get("id")
            if not isinstance(level_id, str) or not level_id:
                continue
            level_order.append(level_id)
            roles = level.get("worker_roles")
            if isinstance(roles, list) and any(
                isinstance(role, str) and role for role in roles
            ):
                worker_eligible_levels.append(level_id)
            else:
                non_delegable_levels.append(level_id)
    executor_selection = _object(source.get("executor_selection"))
    return {
        "schema_version": source.get("schema_version", "unknown"),
        "policy": SOURCE_PATHS["task_decomposition"].as_posix(),
        "plan_template": _string(source.get("plan_template")),
        "default_behavior": _string(source.get("default_behavior")),
        "level_order": level_order,
        "worker_eligible_levels": worker_eligible_levels,
        "non_delegable_levels": non_delegable_levels,
        "small_task_behavior": _string(source.get("small_task_behavior")),
        "executor_selection": {
            "default": _string(executor_selection.get("default"), "primary"),
            "selection_order": _string_list(executor_selection.get("selection_order")),
            "fallback": _string(executor_selection.get("fallback")),
        },
    }


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


def build_agent_entry_packet(
    manifest_text: str,
    router_text: str,
    gate_index_text: str,
    action_authorization_text: str,
    support_policy_text: str,
    task_decomposition_text: str,
    *,
    operation_index_text: str | None = None,
    operation_catalog_text: str | None = None,
    generated_by: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic compact routing packet from target sources."""

    manifest = _load_yaml_text(manifest_text, ".ai/alatyr.yaml")
    router = _load_json_text(router_text, ".ai/assistant/context-router.json")
    _load_json_text(gate_index_text, ".ai/assistant/gates/index.json")
    authorization = _load_json_text(
        action_authorization_text,
        ".ai/assistant/policies/action-authorization.json",
    )
    support_policy = _load_json_text(
        support_policy_text,
        ".ai/project/support-policy.json",
    )
    task_decomposition = _load_json_text(
        task_decomposition_text,
        ".ai/assistant/task-decomposition.json",
    )
    if operation_index_text is not None:
        _load_json_text(operation_index_text, ".ai/assistant/operation-index.json")
    if operation_catalog_text is not None:
        _load_json_text(operation_catalog_text, ".ai/assistant/operation-catalog.json")

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
    classification = _task_classification(router.get("task_classification"))
    compact_classes = {
        class_id: {
            key: value
            for key, value in class_data.items()
            if key in {"task_scale_overlay", "pre_change_preview", "evidence"}
        }
        for class_id, class_data in _object(classification.get("classes")).items()
        if isinstance(class_id, str) and isinstance(class_data, dict)
    }
    decomposition = _task_decomposition_summary(task_decomposition)
    cache_delivery = _object(router.get("cache_aware_delivery"))
    compact_classification = {
        key: classification.get(key)
        for key in [
            "schema_version",
            "classification_order",
            "default_class",
            "ambiguity_behavior",
            "expansion_triggers",
        ]
    }
    compact_classification["classes"] = compact_classes

    return {
        "schema_version": 2,
        "packet_kind": "target-agent-entry-packet",
        "path": PACKET_PATH.as_posix(),
        "generated_by": generated_by or {},
        "derived_from": _derived_from(
            {
                "manifest": manifest_text,
                "context_router": router_text,
                "gate_index": gate_index_text,
                "action_authorization_policy": action_authorization_text,
                "support_policy": support_policy_text,
                "task_decomposition": task_decomposition_text,
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
        "cache_aware_delivery": {
            key: cache_delivery.get(key)
            for key in [
                "schema_version",
                "provider_capability_index",
                "stable_prefix_order",
                "dynamic_tail_order",
                "cache_hit_required",
                "context_window_reduction",
                "fallback",
            ]
        },
        "budget_summary": {
            "bootstrap": _object(context_budgets.get("bootstrap")),
            "profile_default": _object(context_budgets.get("profile_default")),
            "on_exceed": _string(context_budgets.get("on_exceed")),
        },
        "routing_sources": {
            "installed_profile_routes": ".ai/assistant/bootstrap-index.json",
            "profile_descriptors": "profiles",
            "gate_index": SOURCE_PATHS["gate_index"].as_posix(),
            "operation_index": _string(operation_routing.get("index"), "not installed"),
            "operation_catalog": _string(operation_routing.get("catalog"), "not installed"),
            "full_router": SOURCE_PATHS["context_router"].as_posix(),
            "selection_policy": "use bootstrap profile candidates first; load a selected descriptor or canonical owner only for the current task",
        },
        "task_classification": compact_classification,
        "task_decomposition": {
            key: decomposition.get(key)
            for key in [
                "schema_version",
                "policy",
                "plan_template",
                "level_order",
                "non_delegable_levels",
                "default_behavior",
                "executor_selection",
            ]
        },
        "operation_routing": {
            "index": _string(operation_routing.get("index"), "not installed"),
            "catalog": _string(operation_routing.get("catalog"), "not installed"),
            "fallback_operation": _string(
                operation_routing.get("fallback_operation"),
                "help",
            ),
            "load_catalog_when": _string_list(operation_routing.get("load_catalog_when")),
        },
        "authorization": {
            "policy": SOURCE_PATHS["action_authorization_policy"].as_posix(),
            "default_phase": _string(authorization.get("default_phase"), "inspect"),
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
            "support_diff_tool": "tools/alatyr.py support-diff --target <target-repo>",
            "support_delta_tool": (
                "tools/alatyr.py support-delta --target <target-repo> "
                "--diff-ref <base-ref>"
            ),
            "impact_plan_tool": (
                "tools/alatyr.py impact --target <target-repo> "
                "--diff-ref <base-ref>"
            ),
            "approval_scope_check_tool": (
                "tools/alatyr.py approval-check --target <target-repo> "
                "--diff-ref <base-ref> --approval-record <target-approval-json>"
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
        source_texts["task_decomposition"],
        operation_index_text=optional_texts.get("operation_index"),
        operation_catalog_text=optional_texts.get("operation_catalog"),
        generated_by=generation_provenance(
            target,
            tool_name="render_target_entry_packet.py",
        ),
    )


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"
