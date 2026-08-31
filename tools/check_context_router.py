#!/usr/bin/env python3
"""Validate the lazy target context router template.

This validates AlatyrCore source templates only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from task_classification_contract import (
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    LARGE_TASK_CLASS,
    SMALL_TASK_CLASS,
    TARGET_REQUIRED_EXPANSION_TRIGGERS,
    TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
    missing_required_values,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
PROFILES_MD = TARGET / ".ai" / "assistant" / "context-profiles.md"
CONTEXT_PACKET = TARGET / ".ai" / "assistant" / "templates" / "context-packet.json"

CANONICAL_PROFILES = [
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
]
PROFILE_FIELDS = [
    "use_when",
    "operation_candidates",
    "required_context",
    "expand_when",
    "approval_gates",
    "validation",
    "final_evidence",
]
REQUIRED_PRELOADED = ["AGENTS.md"]
REQUIRED_BOOTSTRAP = [
    ".ai/assistant/bootstrap-index.json",
]
FORBIDDEN_BOOTSTRAP = {
    "AGENTS.md",
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
    ".ai/assistant/context-profiles.md",
    ".ai/assistant/module-profile.md",
    ".ai/project/contour.md",
    ".ai/project/source-of-truth-registry.md",
    ".ai/assistant/contour.md",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def require_string_list(
    data: dict[str, Any], key: str, label: str, failures: list[str]
) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        failures.append(f"{label} must contain non-empty list {key}")
        return []
    result = [item for item in value if isinstance(item, str) and item]
    if len(result) != len(value):
        failures.append(f"{label}.{key} must contain only non-empty strings")
    return result


def target_reference_exists(value: str) -> bool:
    if value.startswith("{"):
        return True
    if "{EXTENSION_ID}" in value:
        return value.startswith(".ai/assistant/extensions/{EXTENSION_ID}/") and ".." not in value
    if "{PACKAGE_INSTANCE_ID}" in value:
        return value.startswith(".ai/project/dependencies/snapshots/{PACKAGE_INSTANCE_ID}/") and ".." not in value
    if "{MODE_ID}" in value:
        return value.startswith(".ai/project/workspace-modes/modes/{MODE_ID}/") and ".." not in value
    if value == ".ai/framework":
        return (ROOT / "framework").is_dir()
    if value.startswith(".ai/framework/"):
        return (ROOT / "framework" / value[len(".ai/framework/") :]).is_file()
    if value.startswith(".ai/"):
        return (TARGET / value).exists()
    if value in {"AGENTS.md", "AI_ASSISTANTS.md"}:
        return (TARGET / value).is_file()
    return True


def descriptor(
    reference: Any,
    expected_kind: str,
    label: str,
    failures: list[str],
) -> dict[str, Any]:
    if not isinstance(reference, str) or not reference.startswith(".ai/"):
        failures.append(f"{label}.descriptor must be a target path")
        return {}
    try:
        data = load_json(TARGET / reference)
    except AssertionError as exc:
        failures.append(str(exc))
        return {}
    if data.get("schema_version") != 1:
        failures.append(f"{label} descriptor schema_version must be 1")
    if data.get("descriptor_kind") != expected_kind:
        failures.append(f"{label} descriptor_kind must be {expected_kind}")
    return data


def check_contract(
    data: dict[str, Any],
    fields: list[str],
    label: str,
    failures: list[str],
    path_fields: set[str] | None = None,
) -> None:
    for field in fields:
        values = require_string_list(data, field, label, failures)
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            failures.append(f"{label}.{field} has duplicate values: {duplicates}")
        if field in (path_fields or set()):
            for value in values:
                if not target_reference_exists(value):
                    failures.append(f"{label}.{field} points to missing path: {value}")


def check_conditional_context(
    data: dict[str, Any], label: str, failures: list[str]
) -> list[str]:
    entries = data.get("conditional_context")
    if not isinstance(entries, list) or not entries:
        failures.append(f"{label}.conditional_context must be a non-empty list")
        return []
    paths: list[str] = []
    for index, entry in enumerate(entries):
        entry_label = f"{label}.conditional_context[{index}]"
        if not isinstance(entry, dict):
            failures.append(f"{entry_label} must be an object")
            continue
        path = entry.get("path")
        when = entry.get("when")
        if not isinstance(path, str) or not path:
            failures.append(f"{entry_label}.path must be a non-empty string")
            continue
        if not isinstance(when, str) or not when:
            failures.append(f"{entry_label}.when must be a non-empty string")
        if not target_reference_exists(path):
            failures.append(f"{entry_label}.path points to missing path: {path}")
        paths.append(path)
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    if duplicates:
        failures.append(f"{label}.conditional_context has duplicate paths: {duplicates}")
    return paths


def check_context_packet(router: dict[str, Any], failures: list[str]) -> None:
    packet = router.get("context_packet")
    if not isinstance(packet, dict):
        failures.append("context_packet must be an object")
        return
    if packet.get("schema_version") != 1:
        failures.append("context_packet.schema_version must be 1")
    if packet.get("template") != ".ai/assistant/templates/context-packet.json":
        failures.append("context_packet.template is invalid")
    required_for = packet.get("receipt_required_for")
    for trigger in [
        "semantic codebook fallback",
        "material or protected change",
        "token or cost claim",
    ]:
        if not isinstance(required_for, list) or trigger not in required_for:
            failures.append(f"context_packet receipt trigger missing {trigger}")

    packet_template = load_json(CONTEXT_PACKET)
    required_packet_fields = {
        "schema_version",
        "packet_kind",
        "profile",
        "operation",
        "task_classification",
        "selected_items",
        "semantic_terms",
        "budget",
        "receipt",
        "cost_claim",
        "limitations",
        "packet_digest",
    }
    if set(packet_template) != required_packet_fields:
        failures.append("context packet template fields are invalid")
    receipt_shape = packet_template.get("receipt")
    if not isinstance(receipt_shape, dict):
        failures.append("context packet template must include receipt object")
    else:
        for field in [
            "receipt_kind",
            "measurement_state",
            "planned",
            "resolved",
            "observed",
            "semantic_guidance",
            "task_classification",
        ]:
            if field not in receipt_shape:
                failures.append(f"context packet receipt missing {field}")

    cost_claim = packet_template.get("cost_claim")
    if not isinstance(cost_claim, dict):
        failures.append("context packet template must include cost_claim object")
    else:
        if cost_claim.get("exact_billing_claim") is not False:
            failures.append("context packet exact_billing_claim must default false")
        if cost_claim.get("exact_context_delivery_claim") is not False:
            failures.append("context packet exact_context_delivery_claim must default false")

    limitations = packet_template.get("limitations")
    for required_limitation in [
        "Static source estimates are not billed tokens.",
        "Provider usage alone does not prove exact semantic guidance delivery.",
        "Hidden client context may exist outside repository-visible evidence.",
    ]:
        if not isinstance(limitations, list) or required_limitation not in limitations:
            failures.append(f"context packet limitations missing {required_limitation}")


def check_task_classification(router: dict[str, Any], failures: list[str]) -> None:
    classification = router.get("task_classification")
    if not isinstance(classification, dict):
        failures.append("task_classification must be an object")
        return
    if classification.get("schema_version") != TASK_CLASSIFICATION_SCHEMA_VERSION:
        failures.append("task_classification.schema_version must be 1")
    if classification.get("classification_order") != TASK_CLASSES:
        failures.append("task_classification.classification_order is invalid")
    if classification.get("default_class") != DEFAULT_TASK_CLASS:
        failures.append("task_classification.default_class must be standard-task")
    if AMBIGUITY_READ_ONLY_MARKER not in str(
        classification.get("ambiguity_behavior", "")
    ):
        failures.append("task_classification ambiguity must remain read-only")

    classes = classification.get("classes")
    if not isinstance(classes, dict):
        failures.append("task_classification.classes must be an object")
        classes = {}
    for name in TASK_CLASSES:
        item = classes.get(name)
        if not isinstance(item, dict):
            failures.append(f"task_classification.classes.{name} must be an object")
            continue
        require_string_list(
            item,
            "use_when",
            f"task_classification.classes.{name}",
            failures,
        )
        if name == SMALL_TASK_CLASS:
            if item.get("task_scale_overlay") != SMALL_TASK_CLASS:
                failures.append("small-task class must map to small-task overlay")
            if "compact small-task evidence" not in str(item.get("evidence", "")):
                failures.append("small-task class must name compact evidence")
        if name == LARGE_TASK_CLASS and item.get("task_scale_overlay") != (
            LARGE_TASK_CLASS
        ):
            failures.append("large-or-resumable class must map to large-or-resumable overlay")
        if name == "protected-or-sensitive":
            preview = str(item.get("pre_change_preview", ""))
            if "required" not in preview:
                failures.append("protected-or-sensitive class must require preview")

    triggers = require_string_list(
        classification,
        "expansion_triggers",
        "task_classification",
        failures,
    )
    for required in missing_required_values(
        triggers, TARGET_REQUIRED_EXPANSION_TRIGGERS
    ):
        failures.append(f"task_classification missing expansion trigger {required}")


def main() -> int:
    failures: list[str] = []
    try:
        router = load_json(ROUTER)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if router.get("schema_version") != 10:
        failures.append("context-router.json schema_version must be 10")
    if router.get("router_kind") != "target-context-router":
        failures.append("context-router.json router_kind must be target-context-router")
    if router.get("human_reference") != ".ai/assistant/context-profiles.md":
        failures.append("context-router.json has an invalid human_reference")

    preloaded = require_string_list(router, "preloaded_context", "router", failures)
    bootstrap = require_string_list(router, "bootstrap_context", "router", failures)
    for required in REQUIRED_PRELOADED:
        if required not in preloaded:
            failures.append(f"preloaded_context missing {required}")
    for required in REQUIRED_BOOTSTRAP:
        if required not in bootstrap:
            failures.append(f"bootstrap_context missing {required}")
    if len(set(bootstrap)) != len(bootstrap):
        failures.append("bootstrap_context contains duplicate paths")
    forbidden = sorted(set(bootstrap) & FORBIDDEN_BOOTSTRAP)
    if forbidden:
        failures.append(f"bootstrap_context contains deferred context: {forbidden}")
    if len(bootstrap) > 1:
        failures.append("bootstrap_context must contain only the derived bootstrap index")

    budgets = router.get("context_budgets")
    if not isinstance(budgets, dict):
        failures.append("context_budgets must be an object")
    else:
        bootstrap_budget = budgets.get("bootstrap")
        if not isinstance(bootstrap_budget, dict):
            failures.append("context_budgets.bootstrap must be an object")
            bootstrap_budget = {}
        for field in ["max_files", "max_words"]:
            if not isinstance(bootstrap_budget.get(field), int) or bootstrap_budget[field] <= 0:
                failures.append(f"context_budgets.bootstrap.{field} must be positive")
        profile_budget = budgets.get("profile_default")
        if not isinstance(profile_budget, dict):
            failures.append("context_budgets.profile_default must be an object")
            profile_budget = {}
        for field in [
            "max_files",
            "max_total_words",
            "max_portable_words",
            "reserved_target_words",
        ]:
            if not isinstance(profile_budget.get(field), int) or profile_budget[field] <= 0:
                failures.append(f"context_budgets.profile_default.{field} must be positive")
        total = profile_budget.get("max_total_words")
        portable = profile_budget.get("max_portable_words")
        reserved = profile_budget.get("reserved_target_words")
        if all(isinstance(value, int) for value in [total, portable, reserved]):
            if portable + reserved > total:
                failures.append(
                    "profile max_portable_words plus reserved_target_words exceeds max_total_words"
                )
            if reserved * 10 < total * 3:
                failures.append("template profile budget must reserve at least 30% for target context")
        soft = bootstrap_budget.get("soft_max_words")
        hard = bootstrap_budget.get("max_words")
        if not isinstance(soft, int) or not isinstance(hard, int) or not 0 < soft < hard:
            failures.append("bootstrap soft_max_words must be positive and below max_words")
        if not isinstance(budgets.get("on_exceed"), str) or not budgets["on_exceed"]:
            failures.append("context_budgets.on_exceed must be a non-empty string")

    receipt = router.get("context_receipt")
    if not isinstance(receipt, dict):
        failures.append("context_receipt must be an object")
    else:
        require_string_list(receipt, "required_for", "context_receipt", failures)
        receipt_fields = require_string_list(receipt, "fields", "context_receipt", failures)
        for required in [
            "selected profiles",
            "selected intent overlays",
            "task classification",
            "selected task scale overlay",
            "selected project areas",
            "measurement state",
            "traversed context index chain",
            "selected context item IDs and digests",
            "resolved semantic term IDs and versions",
            "context packet digest",
            "semantic fallback or dictionary expansion",
            "loaded files and reasons",
            "approximate context volume",
            "observed evidence source",
            "token or cost claim classification",
            "hidden client context limitation",
            "expansion triggers",
            "residual risk",
        ]:
            if required not in receipt_fields:
                failures.append(f"context_receipt.fields missing {required}")

    recursive = router.get("recursive_context")
    if not isinstance(recursive, dict):
        failures.append("recursive_context must be an object")
    else:
        if recursive.get("schema_version") != 1:
            failures.append("recursive_context.schema_version must be 1")
        expected_indexes = {
            "framework": ".ai/framework/context-index.json",
            "project": ".ai/project/context-index.json",
            "assistant": ".ai/assistant/context-index.json",
        }
        if recursive.get("contour_indexes") != expected_indexes:
            failures.append("recursive_context.contour_indexes are invalid")
        if recursive.get("max_depth") != 8:
            failures.append("recursive_context.max_depth must be 8")
        if "complete contour" not in str(recursive.get("on_failure", "")):
            failures.append("recursive_context.on_failure must reject broad fallback")

    semantic = router.get("semantic_codebook")
    if not isinstance(semantic, dict):
        failures.append("semantic_codebook must be an object")
    else:
        if semantic.get("schema_version") != 1:
            failures.append("semantic_codebook.schema_version must be 1")
        if semantic.get("index") != ".ai/framework/semantics/index.json":
            failures.append("semantic_codebook.index is invalid")
        if semantic.get("framework_namespace") != "alatyr:*":
            failures.append("semantic codebook framework namespace is invalid")
        if semantic.get("project_namespace") != "project:*":
            failures.append("semantic codebook project namespace is invalid")
        expected_preload = [
            "alatyr:current-scope-authorization@1",
            "alatyr:canonical-owner@1",
            "alatyr:protected-change@1",
            "alatyr:logical-integrity@1",
            "alatyr:bounded-context-expansion@1",
        ]
        if semantic.get("preload_terms") != expected_preload:
            failures.append("semantic_codebook.preload_terms are invalid")
        if "canonical owner" not in str(semantic.get("fallback", "")):
            failures.append("semantic_codebook.fallback must name canonical owner fallback")

    check_context_packet(router, failures)
    check_task_classification(router, failures)

    entry_packet = router.get("agent_entry_packet")
    if not isinstance(entry_packet, dict):
        failures.append("agent_entry_packet must be an object")
    else:
        expected_entry_packet = {
            "schema_version": 1,
            "path": ".ai/assistant/entry-packet.json",
            "load_after": ".ai/assistant/bootstrap-index.json",
        }
        for field, expected in expected_entry_packet.items():
            if entry_packet.get(field) != expected:
                failures.append(f"agent_entry_packet.{field} must be {expected}")
        if "exact installed profile files" not in str(entry_packet.get("purpose", "")):
            failures.append("agent_entry_packet.purpose must describe exact profile files")
        load_reasons = entry_packet.get("load_human_references_when")
        if not isinstance(load_reasons, list) or "ambiguity" not in load_reasons:
            failures.append("agent_entry_packet must define human-reference load reasons")

    operation_routing = router.get("operation_routing")
    if not isinstance(operation_routing, dict):
        failures.append("operation_routing must be an object")
    else:
        expected = {
            "index": ".ai/assistant/operation-index.json",
            "catalog": ".ai/assistant/operation-catalog.json",
            "fallback_operation": "help",
            "health_operation": "adapter-health",
            "single_entry_alias": "Alatyr",
            "preview_policy": "risk-gated",
        }
        for field, value in expected.items():
            if operation_routing.get(field) != value:
                failures.append(f"operation_routing.{field} must be {value}")
        require_string_list(operation_routing, "load_index_when", "operation_routing", failures)
        require_string_list(operation_routing, "load_catalog_when", "operation_routing", failures)

    routing_order = require_string_list(router, "routing_order", "router", failures)
    if routing_order != CANONICAL_PROFILES:
        failures.append("routing_order must match canonical profile order")

    profile_index = router.get("profile_index")
    profiles: dict[str, dict[str, Any]] = {}
    profile_conditional_context: list[str] = []
    if not isinstance(profile_index, dict):
        failures.append("profile_index must be an object")
        profile_index = {}
    markdown_names = set(
        re.findall(
            r"^## Profile: `([^`]+)`",
            PROFILES_MD.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
    )
    for name in CANONICAL_PROFILES:
        if name not in markdown_names:
            failures.append(f"context-profiles.md missing profile {name}")
        entry = profile_index.get(name)
        if not isinstance(entry, dict):
            failures.append(f"profile_index.{name} must be an object")
            continue
        require_string_list(entry, "use_when", f"profile_index.{name}", failures)
        profile = descriptor(
            entry.get("descriptor"), "target-context-profile", f"profile_index.{name}", failures
        )
        if profile.get("profile") != name:
            failures.append(f"profile descriptor identity differs for {name}")
        check_contract(
            profile,
            PROFILE_FIELDS,
            f"profiles.{name}",
            failures,
            {"required_context", "validation"},
        )
        if "conditional_context" in profile:
            profile_conditional_context.extend(
                check_conditional_context(profile, f"profiles.{name}", failures)
            )
        profiles[name] = profile
    extras = sorted(set(profile_index) - set(CANONICAL_PROFILES))
    if extras:
        failures.append(f"context-router.json has unexpected profiles: {extras}")

    cost_scenario_entry = router.get("cost_scenarios")
    cost_scenario_contract = descriptor(
        cost_scenario_entry.get("descriptor")
        if isinstance(cost_scenario_entry, dict)
        else None,
        "target-context-cost-scenarios",
        "cost_scenarios",
        failures,
    )
    cost_scenarios = cost_scenario_contract.get("scenarios")
    if not isinstance(cost_scenarios, dict) or not cost_scenarios:
        failures.append("cost scenario descriptor must contain scenarios")
    else:
        for name, scenario in cost_scenarios.items():
            if not isinstance(scenario, dict):
                failures.append(f"cost_scenarios.{name} must be an object")
                continue
            if scenario.get("profile") not in CANONICAL_PROFILES:
                failures.append(f"cost_scenarios.{name} selects an unknown profile")
            for field, available in [
                ("intent_overlays", set((router.get("intent_overlays") or {}).keys())),
                ("task_scale_overlays", set((router.get("task_scale_overlays") or {}).keys())),
            ]:
                values = scenario.get(field)
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value in available for value in values
                ):
                    failures.append(f"cost_scenarios.{name}.{field} is invalid")
            if scenario.get("expected_budget_state") not in {
                "compact",
                "expansion-receipt-required",
            }:
                failures.append(f"cost_scenarios.{name} has invalid budget state")

    intent_index = router.get("intent_overlays")
    diagram: dict[str, Any] = {}
    diagram_conditional_context: list[str] = []
    architecture: dict[str, Any] = {}
    architecture_conditional_context: list[str] = []
    code_documentation: dict[str, Any] = {}
    code_documentation_conditional_context: list[str] = []
    vocabulary: dict[str, Any] = {}
    vocabulary_conditional_context: list[str] = []
    test_first: dict[str, Any] = {}
    test_first_conditional_context: list[str] = []
    extension: dict[str, Any] = {}
    extension_conditional_context: list[str] = []
    dependency_knowledge: dict[str, Any] = {}
    dependency_knowledge_conditional_context: list[str] = []
    workspace_mode: dict[str, Any] = {}
    workspace_mode_conditional_context: list[str] = []
    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("diagram-request"), dict
    ):
        failures.append("intent_overlays.diagram-request must be indexed")
    else:
        entry = intent_index["diagram-request"]
        diagram = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.diagram-request",
            failures,
        )
        check_contract(
            diagram,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.diagram-request",
            failures,
            {"required_context"},
        )
        if diagram.get("required_module") != "diagrams":
            failures.append("diagram intent must require diagrams")
        if diagram.get("operation_candidates") != ["diagram-discussion"]:
            failures.append("diagram intent must route diagram-discussion")
        diagram_conditional_context = check_conditional_context(
            diagram, "intent_overlays.diagram-request", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("architecture-request"), dict
    ):
        failures.append("intent_overlays.architecture-request must be indexed")
    else:
        entry = intent_index["architecture-request"]
        architecture = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.architecture-request",
            failures,
        )
        check_contract(
            architecture,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.architecture-request",
            failures,
            {"required_context"},
        )
        if architecture.get("required_module") != "architecture-knowledge":
            failures.append(
                "architecture intent must require architecture-knowledge"
            )
        if architecture.get("operation_candidates") != ["architecture-assistance"]:
            failures.append(
                "architecture intent must route architecture-assistance"
            )
        architecture_conditional_context = check_conditional_context(
            architecture, "intent_overlays.architecture-request", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("code-documentation"), dict
    ):
        failures.append("intent_overlays.code-documentation must be indexed")
    else:
        entry = intent_index["code-documentation"]
        code_documentation = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.code-documentation",
            failures,
        )
        check_contract(
            code_documentation,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.code-documentation",
            failures,
            {"required_context"},
        )
        if code_documentation.get("required_module") != "code-documentation":
            failures.append(
                "code-documentation intent must require code-documentation"
            )
        if code_documentation.get("operation_candidates") != ["documentation-sync"]:
            failures.append(
                "code-documentation intent must route documentation-sync"
            )
        code_documentation_conditional_context = check_conditional_context(
            code_documentation, "intent_overlays.code-documentation", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("vocabulary-request"), dict
    ):
        failures.append("intent_overlays.vocabulary-request must be indexed")
    else:
        entry = intent_index["vocabulary-request"]
        vocabulary = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.vocabulary-request",
            failures,
        )
        check_contract(
            vocabulary,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.vocabulary-request",
            failures,
            {"required_context"},
        )
        if vocabulary.get("required_module") != "project-vocabulary":
            failures.append(
                "vocabulary intent must require project-vocabulary"
            )
        if vocabulary.get("operation_candidates") != ["project-vocabulary"]:
            failures.append(
                "vocabulary intent must route project-vocabulary"
            )
        vocabulary_conditional_context = check_conditional_context(
            vocabulary, "intent_overlays.vocabulary-request", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("test-first-request"), dict
    ):
        failures.append("intent_overlays.test-first-request must be indexed")
    else:
        entry = intent_index["test-first-request"]
        test_first = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.test-first-request",
            failures,
        )
        check_contract(
            test_first,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.test-first-request",
            failures,
            {"required_context"},
        )
        if test_first.get("required_module") != "core-profile":
            failures.append("test-first intent must permit core-profile configuration")
        if test_first.get("operation_candidates") != [
            "test-first-configuration",
            "test-first-change",
        ]:
            failures.append(
                "test-first intent must route configuration before enabled execution"
            )
        test_first_conditional_context = check_conditional_context(
            test_first, "intent_overlays.test-first-request", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("extension-request"), dict
    ):
        failures.append("intent_overlays.extension-request must be indexed")
    else:
        entry = intent_index["extension-request"]
        extension = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.extension-request",
            failures,
        )
        check_contract(
            extension,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.extension-request",
            failures,
            {"required_context"},
        )
        if extension.get("required_module") != "core-profile":
            failures.append("extension intent must permit core-profile inspection")
        if extension.get("operation_candidates") != ["extension-management"]:
            failures.append("extension intent must route extension-management")
        extension_conditional_context = check_conditional_context(
            extension, "intent_overlays.extension-request", failures
        )

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("dependency-knowledge-request"), dict
    ):
        failures.append("intent_overlays.dependency-knowledge-request must be indexed")
    else:
        entry = intent_index["dependency-knowledge-request"]
        dependency_knowledge = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.dependency-knowledge-request",
            failures,
        )
        check_contract(
            dependency_knowledge,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.dependency-knowledge-request",
            failures,
            {"required_context"},
        )
        if dependency_knowledge.get("required_module") != "dependency-knowledge":
            failures.append("dependency knowledge intent must require dependency-knowledge")
        if dependency_knowledge.get("operation_candidates") != ["dependency-knowledge"]:
            failures.append("dependency knowledge intent must route dependency-knowledge")
        dependency_knowledge_conditional_context = check_conditional_context(
            dependency_knowledge,
            "intent_overlays.dependency-knowledge-request",
            failures,
        )

    workspace_routing = router.get("workspace_mode_routing")
    if not isinstance(workspace_routing, dict):
        failures.append("workspace_mode_routing must be an object")
    else:
        expected_mode_routing = {
            "required_module": "workspace-modes",
            "catalog": ".ai/project/workspace-modes/catalog.json",
            "root_context": ".ai/project/workspace-modes/root/context.json",
            "mode_path_pattern": ".ai/project/workspace-modes/modes/{MODE_ID}/mode.json",
            "ambiguity_behavior": "ask-user-and-remain-read-only",
            "no_match_behavior": "root-read-only",
            "preflight": ".ai/assistant/templates/workspace-mode-preflight.md",
        }
        for field, expected in expected_mode_routing.items():
            if workspace_routing.get(field) != expected:
                failures.append(f"workspace_mode_routing.{field} must be {expected}")
        selection_order = workspace_routing.get("selection_order")
        if not isinstance(selection_order, list) or len(selection_order) != 3 or not all(
            isinstance(value, str) and value for value in selection_order
        ):
            failures.append("workspace_mode_routing.selection_order must contain three steps")

    if not isinstance(intent_index, dict) or not isinstance(
        intent_index.get("workspace-mode-request"), dict
    ):
        failures.append("intent_overlays.workspace-mode-request must be indexed")
    else:
        entry = intent_index["workspace-mode-request"]
        workspace_mode = descriptor(
            entry.get("descriptor"),
            "target-intent-overlay",
            "intent_overlays.workspace-mode-request",
            failures,
        )
        check_contract(
            workspace_mode,
            ["use_when", "operation_candidates", "required_context", "expand_when"],
            "intent_overlays.workspace-mode-request",
            failures,
            {"required_context"},
        )
        if workspace_mode.get("required_module") != "workspace-modes":
            failures.append("workspace mode intent must require workspace-modes")
        if workspace_mode.get("operation_candidates") != ["workspace-mode"]:
            failures.append("workspace mode intent must route workspace-mode")
        workspace_mode_conditional_context = check_conditional_context(
            workspace_mode,
            "intent_overlays.workspace-mode-request",
            failures,
        )

    consistency_entry = router.get("consistency_routing")
    consistency = descriptor(
        consistency_entry.get("descriptor") if isinstance(consistency_entry, dict) else None,
        "target-consistency-routing",
        "consistency_routing",
        failures,
    )
    check_contract(
        consistency,
        ["enabled_when", "required_context", "lookup_order", "expand_when", "final_evidence"],
        "consistency_routing",
        failures,
        {"required_context"},
    )
    consistency_required = consistency.get("required_context", [])
    for required in [
        ".ai/project/source-of-truth-registry.md",
        ".ai/project/consistency-map.json",
    ]:
        if required not in consistency_required:
            failures.append(f"consistency_routing missing {required}")
    if ".ai/framework/consistency-model.md" in consistency_required:
        failures.append(
            "consistency_routing should keep portable consistency-model guidance conditional"
        )
    consistency_conditional = check_conditional_context(
        consistency,
        "consistency_routing",
        failures,
    )
    if ".ai/framework/consistency-model.md" not in consistency_conditional:
        failures.append(
            "consistency_routing conditional context missing portable consistency-model guidance"
        )

    knowledge_entry = router.get("project_knowledge_routing")
    project_knowledge = descriptor(
        knowledge_entry.get("descriptor") if isinstance(knowledge_entry, dict) else None,
        "target-project-knowledge-routing",
        "project_knowledge_routing",
        failures,
    )
    if not isinstance(knowledge_entry, dict):
        failures.append("project_knowledge_routing must be indexed")
    else:
        if knowledge_entry.get("profile_only_match_allowed") is not False:
            failures.append("project knowledge routing must reject profile-only matches")
        for field in ["initial_after", "refined_after"]:
            if not isinstance(knowledge_entry.get(field), str) or not knowledge_entry[field]:
                failures.append(f"project_knowledge_routing.{field} must be recorded")
    check_contract(
        project_knowledge,
        [
            "enabled_when",
            "initial_selectors",
            "refined_selectors",
            "delivery_rules",
            "expand_when",
            "context_receipt",
        ],
        "project_knowledge_routing",
        failures,
    )
    if project_knowledge.get("index") != ".ai/project/knowledge/index.json":
        failures.append("project knowledge route must use its compact target index")
    if not isinstance(project_knowledge.get("budget_behavior"), str):
        failures.append("project knowledge route must define budget_behavior")
    knowledge_receipt = project_knowledge.get("context_receipt", [])
    for required in [
        "ordered planned resolved and observed guidance identities",
        "canonical owner digests authority freshness and applicability",
        "semantic guidance bundle digest algorithm and schema version",
    ]:
        if required not in knowledge_receipt:
            failures.append(f"project knowledge context receipt missing {required}")
    project_knowledge_conditional_context = check_conditional_context(
        project_knowledge,
        "project_knowledge_routing",
        failures,
    )
    if ".ai/framework/project-knowledge.md" not in project_knowledge_conditional_context:
        failures.append("project knowledge route must keep its portable owner conditionally available")

    migration_entry = router.get("migration_routing")
    migration = descriptor(
        migration_entry.get("descriptor") if isinstance(migration_entry, dict) else None,
        "target-migration-routing",
        "migration_routing",
        failures,
    )
    if not isinstance(migration_entry, dict) or migration_entry.get(
        "assessment_required_before_changes"
    ) is not True:
        failures.append("migration assessment must be required before changes")
    check_contract(
        migration,
        ["required_context", "impact_selectors", "candidate_context", "expand_when", "final_evidence"],
        "migration_routing",
        failures,
        {"required_context", "candidate_context"},
    )

    scale_index = router.get("task_scale_overlays")
    large_task: dict[str, Any] = {}
    if not isinstance(scale_index, dict):
        failures.append("task_scale_overlays must be an object")
        scale_index = {}
    small_entry = scale_index.get(SMALL_TASK_CLASS)
    small_task = descriptor(
        small_entry.get("descriptor") if isinstance(small_entry, dict) else None,
        "target-task-scale-overlay",
        "task_scale_overlays.small-task",
        failures,
    )
    check_contract(
        small_task,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.small-task",
        failures,
        {"required_context"},
    )
    if ".ai/assistant/gates/core.md" not in small_task.get("required_context", []):
        failures.append("small-task overlay must load the core gate fragment")
    if ".ai/assistant/gates/final-evidence.md" not in small_task.get(
        "required_context", []
    ):
        failures.append("small-task overlay must load final-evidence gate fragment")
    if not isinstance(small_task.get("budget_behavior"), str):
        failures.append("small-task overlay needs budget_behavior")
    elif "large-task" not in small_task["budget_behavior"]:
        failures.append("small-task overlay must keep large-task routing lazy")
    small_task_conditional = check_conditional_context(
        small_task, "task_scale_overlays.small-task", failures
    )
    if ".ai/assistant/templates/small-task-evidence.md" not in small_task_conditional:
        failures.append("small-task overlay must route compact evidence template lazily")
    for required in missing_required_values(
        small_task.get("expand_when", []),
        TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS,
    ):
        failures.append(f"small-task overlay missing expansion trigger {required}")
    large_entry = scale_index.get(LARGE_TASK_CLASS)
    large_task = descriptor(
        large_entry.get("descriptor") if isinstance(large_entry, dict) else None,
        "target-task-scale-overlay",
        "task_scale_overlays.large-or-resumable",
        failures,
    )
    check_contract(
        large_task,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.large-or-resumable",
        failures,
        {"required_context"},
    )
    if not isinstance(large_task.get("budget_behavior"), str):
        failures.append("large task overlay needs budget_behavior")
    elif "only new or changed owners" not in large_task["budget_behavior"]:
        failures.append("large task overlay must keep guidance reloads delta-only")
    revalidation = large_task.get("semantic_guidance_revalidation")
    if not isinstance(revalidation, dict):
        failures.append("large task overlay needs semantic_guidance_revalidation")
    else:
        expected_revalidation = {
            "receipt_contract": "alatyr-context-receipt semantic_guidance schema 1",
            "comparison_surface": (
                "current resolved ordered bundle digest versus last accepted "
                "checkpoint digest"
            ),
            "claim_boundary": (
                "bundle identity is not proof of model comprehension or compliance"
            ),
        }
        for field, expected in expected_revalidation.items():
            if revalidation.get(field) != expected:
                failures.append(
                    f"large task semantic_guidance_revalidation.{field} must be {expected}"
                )
        required_before = revalidation.get("required_before")
        expected_gates = [
            "protected implementation",
            "material decisions",
            "final validation",
            "final evidence",
        ]
        if required_before != expected_gates:
            failures.append(
                "large task semantic guidance revalidation gates are incomplete or unordered"
            )
        on_difference = revalidation.get("on_difference")
        for required in [
            "stop the affected phase",
            "load only changed owners",
            "refresh risk approval dependencies and validation",
        ]:
            if not isinstance(on_difference, str) or required not in on_difference:
                failures.append(
                    f"large task semantic guidance difference handling missing {required}"
                )
    if (
        "resolved semantic guidance bundle differs from the last accepted checkpoint"
        not in large_task.get("expand_when", [])
    ):
        failures.append("large task overlay must expand on semantic guidance bundle drift")
    large_final_evidence = large_task.get("final_evidence", [])
    for required in [
        "planned resolved and observed semantic guidance identities and ordered bundle digests",
        "revalidation gate results and checkpoints",
    ]:
        if required not in large_final_evidence:
            failures.append(f"large task final evidence missing {required}")
    delegated_entry = scale_index.get("delegated-execution")
    delegated = descriptor(
        delegated_entry.get("descriptor")
        if isinstance(delegated_entry, dict)
        else None,
        "target-task-scale-overlay",
        "task_scale_overlays.delegated-execution",
        failures,
    )
    check_contract(
        delegated,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.delegated-execution",
        failures,
        {"required_context"},
    )
    if not isinstance(delegated.get("budget_behavior"), str):
        failures.append("delegated execution overlay needs budget_behavior")
    package_entry = scale_index.get("change-package")
    change_package = descriptor(
        package_entry.get("descriptor") if isinstance(package_entry, dict) else None,
        "target-task-scale-overlay",
        "task_scale_overlays.change-package",
        failures,
    )
    check_contract(
        change_package,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.change-package",
        failures,
        {"required_context"},
    )
    if not isinstance(change_package.get("budget_behavior"), str):
        failures.append("change package overlay needs budget_behavior")
    change_package_conditional_context = check_conditional_context(
        change_package, "task_scale_overlays.change-package", failures
    )
    evidence_entry = scale_index.get("engineering-evidence")
    engineering_evidence = descriptor(
        evidence_entry.get("descriptor") if isinstance(evidence_entry, dict) else None,
        "target-task-scale-overlay",
        "task_scale_overlays.engineering-evidence",
        failures,
    )
    check_contract(
        engineering_evidence,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.engineering-evidence",
        failures,
        {"required_context"},
    )
    if not isinstance(engineering_evidence.get("budget_behavior"), str):
        failures.append("engineering evidence overlay needs budget_behavior")
    engineering_evidence_conditional_context = check_conditional_context(
        engineering_evidence,
        "task_scale_overlays.engineering-evidence",
        failures,
    )
    debug_entry = scale_index.get("debug-mode")
    debug_mode = descriptor(
        debug_entry.get("descriptor") if isinstance(debug_entry, dict) else None,
        "target-task-scale-overlay",
        "task_scale_overlays.debug-mode",
        failures,
    )
    check_contract(
        debug_mode,
        ["use_when", "required_context", "expand_when", "final_evidence"],
        "task_scale_overlays.debug-mode",
        failures,
        {"required_context"},
    )
    if not isinstance(debug_mode.get("budget_behavior"), str):
        failures.append("Debug Mode overlay needs budget_behavior")
    debug_mode_conditional_context = check_conditional_context(
        debug_mode,
        "task_scale_overlays.debug-mode",
        failures,
    )
    team_entry = scale_index.get("team-active")
    if not isinstance(team_entry, dict) or team_entry.get("descriptor") != (
        ".ai/assistant/team/context-overlay.json"
    ):
        failures.append("team-active must point to its lazy descriptor")

    area_overlays = router.get("area_overlays")
    if not isinstance(area_overlays, dict) or not area_overlays:
        failures.append("area_overlays must be a non-empty object")
    else:
        for name, overlay in area_overlays.items():
            if isinstance(overlay, dict):
                check_contract(
                    overlay,
                    ["use_when", "required_context", "expand_when"],
                    f"area_overlays.{name}",
                    failures,
                )
            else:
                failures.append(f"area_overlays.{name} must be an object")

    upgrade_context = profiles.get("framework-upgrade", {}).get("required_context", [])
    if len(upgrade_context) > 8:
        failures.append("framework-upgrade required_context must remain migration-first")

    framework_paths = {
        f".ai/framework/{path.relative_to(ROOT / 'framework').as_posix()}"
        for path in (ROOT / "framework").rglob("*.md")
    }
    routed_framework_paths = {
        value
        for profile in profiles.values()
        for value in profile.get("required_context", [])
        if isinstance(value, str) and value.startswith(".ai/framework/")
    }
    routed_framework_paths.update(
        value
        for value in profile_conditional_context
        if value.startswith(".ai/framework/")
    )
    for contract, field in [
        (consistency, "required_context"),
        (migration, "candidate_context"),
        (large_task, "required_context"),
        (delegated, "required_context"),
        (change_package, "required_context"),
        (engineering_evidence, "required_context"),
        (debug_mode, "required_context"),
        (project_knowledge, "required_context"),
        (diagram, "required_context"),
        (architecture, "required_context"),
        (code_documentation, "required_context"),
        (vocabulary, "required_context"),
        (test_first, "required_context"),
        (extension, "required_context"),
        (dependency_knowledge, "required_context"),
        (workspace_mode, "required_context"),
    ]:
        routed_framework_paths.update(
            value
            for value in contract.get(field, [])
            if isinstance(value, str) and value.startswith(".ai/framework/")
        )
    routed_framework_paths.update(
        value
        for value in diagram_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in change_package_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in engineering_evidence_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in debug_mode_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in project_knowledge_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in architecture_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in code_documentation_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in vocabulary_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in test_first_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in extension_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in dependency_knowledge_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in workspace_mode_conditional_context
        if value.startswith(".ai/framework/")
    )
    try:
        ai_router = load_json(TARGET / ".ai/assistant/ai-infrastructure-router.json")
        for route in ai_router.get("routes", {}).values():
            if isinstance(route, dict):
                routed_framework_paths.update(
                    value
                    for value in route.get("required_context", [])
                    if isinstance(value, str) and value.startswith(".ai/framework/")
                )
    except AssertionError as exc:
        failures.append(str(exc))
    missing = sorted(framework_paths - routed_framework_paths)
    if missing:
        failures.append(f"context routing omits framework files: {missing}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: checked lazy context router template with {len(profiles)} profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
