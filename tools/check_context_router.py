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


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"
PROFILES_MD = TARGET / ".ai" / "assistant" / "context-profiles.md"

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
    ".ai/alatyr.yaml",
    ".ai/README.md",
    ".ai/assistant/context-router.json",
]
FORBIDDEN_BOOTSTRAP = {
    "AGENTS.md",
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


def main() -> int:
    failures: list[str] = []
    try:
        router = load_json(ROUTER)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if router.get("schema_version") != 3:
        failures.append("context-router.json schema_version must be 3")
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
    if len(bootstrap) > 4:
        failures.append("bootstrap_context must contain at most 4 files")

    budgets = router.get("context_budgets")
    if not isinstance(budgets, dict):
        failures.append("context_budgets must be an object")
    else:
        for name in ["bootstrap", "profile_default"]:
            budget = budgets.get(name)
            if not isinstance(budget, dict):
                failures.append(f"context_budgets.{name} must be an object")
                continue
            for field in ["max_files", "max_words"]:
                if not isinstance(budget.get(field), int) or budget[field] <= 0:
                    failures.append(f"context_budgets.{name}.{field} must be positive")
        bootstrap_budget = budgets.get("bootstrap", {})
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
            "selected task scale overlay",
            "selected project areas",
            "loaded files and reasons",
            "approximate context volume",
            "expansion triggers",
            "residual risk",
        ]:
            if required not in receipt_fields:
                failures.append(f"context_receipt.fields missing {required}")

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
        profiles[name] = profile
    extras = sorted(set(profile_index) - set(CANONICAL_PROFILES))
    if extras:
        failures.append(f"context-router.json has unexpected profiles: {extras}")

    intent_index = router.get("intent_overlays")
    diagram: dict[str, Any] = {}
    diagram_conditional_context: list[str] = []
    architecture: dict[str, Any] = {}
    architecture_conditional_context: list[str] = []
    code_documentation: dict[str, Any] = {}
    code_documentation_conditional_context: list[str] = []
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
    large_entry = scale_index.get("large-or-resumable")
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
        f".ai/framework/{path.name}" for path in (ROOT / "framework").glob("*.md")
    }
    routed_framework_paths = {
        value
        for profile in profiles.values()
        for value in profile.get("required_context", [])
        if isinstance(value, str) and value.startswith(".ai/framework/")
    }
    for contract, field in [
        (consistency, "required_context"),
        (migration, "candidate_context"),
        (large_task, "required_context"),
        (change_package, "required_context"),
        (diagram, "required_context"),
        (architecture, "required_context"),
        (code_documentation, "required_context"),
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
        for value in architecture_conditional_context
        if value.startswith(".ai/framework/")
    )
    routed_framework_paths.update(
        value
        for value in code_documentation_conditional_context
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
