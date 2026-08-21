#!/usr/bin/env python3
"""Measure deterministic target-template context routing costs."""

from __future__ import annotations

import argparse
import math
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
ROUTER = TARGET / ".ai" / "assistant" / "context-router.json"


def source_path(reference: str) -> Path | None:
    if "{" in reference:
        return None
    if reference.startswith(".ai/framework/"):
        return ROOT / "framework" / reference[len(".ai/framework/") :]
    if reference.startswith(".ai/"):
        return TARGET / reference
    if reference in {"AGENTS.md", "AI_ASSISTANTS.md"}:
        return TARGET / reference
    return None


def installed_path(target: Path, reference: str) -> Path | None:
    if "{" in reference:
        return None
    if reference.startswith(".ai/") or reference in {"AGENTS.md", "AI_ASSISTANTS.md"}:
        return target / reference
    if reference.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", reference):
        return None
    return target / reference


def measure_installed(target: Path, references: list[str]) -> dict[str, Any]:
    unique = list(dict.fromkeys(references))
    resolved: list[tuple[str, Path]] = []
    unresolved: list[str] = []
    missing: list[str] = []
    for reference in unique:
        path = installed_path(target, reference)
        if path is None:
            unresolved.append(reference)
        elif not path.is_file():
            missing.append(reference)
        else:
            resolved.append((reference, path))
    texts = [path.read_text(encoding="utf-8") for _, path in resolved]
    characters = sum(len(value) for value in texts)
    word_counts = {
        reference: len(re.findall(r"\S+", path.read_text(encoding="utf-8")))
        for reference, path in resolved
    }
    portable_paths = [
        reference for reference, _ in resolved if reference.startswith(".ai/framework/")
    ]
    target_paths = [
        reference for reference, _ in resolved if reference not in portable_paths
    ]
    return {
        "declared_files": len(unique),
        "resolved_files": len(resolved),
        "words": sum(len(re.findall(r"\S+", value)) for value in texts),
        "portable_words": sum(word_counts[path] for path in portable_paths),
        "target_words": sum(word_counts[path] for path in target_paths),
        "characters": characters,
        "bytes": sum(len(value.encode("utf-8")) for value in texts),
        "estimated_tokens_4_chars": math.ceil(characters / 4),
        "resolved_paths": [reference for reference, _ in resolved],
        "portable_paths": portable_paths,
        "target_paths": target_paths,
        "unresolved_references": unresolved,
        "missing_paths": missing,
    }


def measure(references: list[str]) -> dict[str, Any]:
    unique = list(dict.fromkeys(references))
    resolved: list[tuple[str, Path]] = []
    unresolved: list[str] = []
    missing: list[str] = []
    for reference in unique:
        path = source_path(reference)
        if path is None:
            unresolved.append(reference)
        elif not path.is_file():
            missing.append(reference)
        else:
            resolved.append((reference, path))
    texts = [path.read_text(encoding="utf-8") for _, path in resolved]
    characters = sum(len(value) for value in texts)
    word_counts = {
        reference: len(re.findall(r"\S+", path.read_text(encoding="utf-8")))
        for reference, path in resolved
    }
    portable_paths = [
        reference for reference, _ in resolved if reference.startswith(".ai/framework/")
    ]
    target_paths = [
        reference for reference, _ in resolved if reference not in portable_paths
    ]
    return {
        "declared_files": len(unique),
        "resolved_files": len(resolved),
        "words": sum(len(re.findall(r"\S+", value)) for value in texts),
        "portable_words": sum(word_counts[path] for path in portable_paths),
        "target_words": sum(word_counts[path] for path in target_paths),
        "characters": characters,
        "bytes": sum(len(value.encode("utf-8")) for value in texts),
        "estimated_tokens_4_chars": math.ceil(characters / 4),
        "resolved_paths": [reference for reference, _ in resolved],
        "portable_paths": portable_paths,
        "target_paths": target_paths,
        "unresolved_references": unresolved,
        "missing_paths": missing,
    }


def reduction_percent(initial: int, full: int) -> float | str:
    if full <= 0:
        return "unknown"
    return round((1 - initial / full) * 100, 1)


def build_report() -> dict[str, Any]:
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    bootstrap_refs = [
        *router.get("preloaded_context", []),
        *router.get("bootstrap_context", []),
    ]
    bootstrap = measure(bootstrap_refs)
    def descriptor(entry: Any) -> tuple[str | None, dict[str, Any]]:
        reference = entry.get("descriptor") if isinstance(entry, dict) else None
        path = source_path(reference) if isinstance(reference, str) else None
        if path is None or not path.is_file():
            return reference, {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return reference, data if isinstance(data, dict) else {}

    profiles: dict[str, dict[str, Any]] = {}
    profile_contracts: dict[str, tuple[str | None, dict[str, Any]]] = {}
    for name, entry in router.get("profile_index", {}).items():
        reference, profile = descriptor(entry)
        profile_contracts[name] = (reference, profile)
        profile_measure = measure(
            [value for value in [reference, *profile.get("required_context", [])] if value]
        )
        conditional_refs = [
            item.get("path")
            for item in profile.get("conditional_context", [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        ]
        profile_measure["conditional_context"] = measure(conditional_refs)
        profile_measure["full_candidate_union"] = measure(
            [
                value
                for value in [
                    reference,
                    *profile.get("required_context", []),
                    *conditional_refs,
                ]
                if value
            ]
        )
        profiles[name] = profile_measure

    intent_overlays: dict[str, dict[str, Any]] = {}
    intent_contracts: dict[str, tuple[str | None, dict[str, Any]]] = {}
    capability_index = json.loads(
        (TARGET / ".ai/assistant/assistant-capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    default_surface = capability_index.get("default_surface")
    default_capability = capability_index.get("surfaces", {}).get(default_surface)
    for name, overlay in router.get("intent_overlays", {}).items():
        reference, contract = descriptor(overlay)
        intent_contracts[name] = (reference, contract)
        surface_context = [default_capability] if name == "diagram-request" else []
        intent_overlays[name] = measure(
            [
                value
                for value in [
                    reference,
                    *contract.get("required_context", []),
                    *surface_context,
                ]
                if value
            ]
        )

    task_scale_overlays: dict[str, dict[str, Any]] = {}
    task_scale_contracts: dict[str, tuple[str | None, dict[str, Any]]] = {}
    for name, overlay in router.get("task_scale_overlays", {}).items():
        reference, contract = descriptor(overlay)
        task_scale_contracts[name] = (reference, contract)
        task_scale_overlays[name] = measure(
            [
                value
                for value in [
                    reference,
                    *contract.get("required_context", []),
                ]
                if value
            ]
        )

    operation_routing = router.get("operation_routing", {})
    diagram_reference, diagram_overlay = intent_contracts.get(
        "diagram-request", (None, {})
    )
    diagram_compact_refs = [
        operation_routing.get("index", ""),
        diagram_reference,
        *diagram_overlay.get("required_context", []),
        default_capability,
    ]
    diagram_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        ".ai/assistant/bridge-capability-matrix.md",
        diagram_reference,
        *diagram_overlay.get("required_context", []),
        default_capability,
    ]
    diagram_compact = measure([value for value in diagram_compact_refs if value])
    diagram_full_reference = measure(
        [value for value in diagram_full_reference_refs if value]
    )

    architecture_reference, architecture_overlay = intent_contracts.get(
        "architecture-request", (None, {})
    )
    architecture_conditional_refs = [
        entry.get("path")
        for entry in architecture_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    architecture_compact_refs = [
        operation_routing.get("index", ""),
        architecture_reference,
        *architecture_overlay.get("required_context", []),
    ]
    architecture_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        architecture_reference,
        *architecture_overlay.get("required_context", []),
        *architecture_conditional_refs,
    ]
    architecture_compact = measure(
        [value for value in architecture_compact_refs if value]
    )
    architecture_full_reference = measure(
        [value for value in architecture_full_reference_refs if value]
    )

    code_documentation_reference, code_documentation_overlay = intent_contracts.get(
        "code-documentation", (None, {})
    )
    code_documentation_conditional_refs = [
        entry.get("path")
        for entry in code_documentation_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    code_documentation_compact_refs = [
        operation_routing.get("index", ""),
        code_documentation_reference,
        *code_documentation_overlay.get("required_context", []),
    ]
    code_documentation_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        code_documentation_reference,
        *code_documentation_overlay.get("required_context", []),
        *code_documentation_conditional_refs,
    ]
    code_documentation_compact = measure(
        [value for value in code_documentation_compact_refs if value]
    )
    code_documentation_full_reference = measure(
        [value for value in code_documentation_full_reference_refs if value]
    )

    vocabulary_reference, vocabulary_overlay = intent_contracts.get(
        "vocabulary-request", (None, {})
    )
    vocabulary_conditional_refs = [
        entry.get("path")
        for entry in vocabulary_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    vocabulary_compact_refs = [
        operation_routing.get("index", ""),
        vocabulary_reference,
        *vocabulary_overlay.get("required_context", []),
    ]
    vocabulary_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        vocabulary_reference,
        *vocabulary_overlay.get("required_context", []),
        *vocabulary_conditional_refs,
    ]
    vocabulary_compact = measure(
        [value for value in vocabulary_compact_refs if value]
    )
    vocabulary_full_reference = measure(
        [value for value in vocabulary_full_reference_refs if value]
    )

    test_first_reference, test_first_overlay = intent_contracts.get(
        "test-first-request", (None, {})
    )
    test_first_conditional_refs = [
        entry.get("path")
        for entry in test_first_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    test_first_compact_refs = [
        operation_routing.get("index", ""),
        test_first_reference,
        *test_first_overlay.get("required_context", []),
    ]
    test_first_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        test_first_reference,
        *test_first_overlay.get("required_context", []),
        *test_first_conditional_refs,
    ]
    test_first_compact = measure(
        [value for value in test_first_compact_refs if value]
    )
    test_first_full_reference = measure(
        [value for value in test_first_full_reference_refs if value]
    )

    extension_reference, extension_overlay = intent_contracts.get(
        "extension-request", (None, {})
    )
    extension_conditional_refs = [
        entry.get("path")
        for entry in extension_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    extension_compact_refs = [
        operation_routing.get("index", ""),
        extension_reference,
        *extension_overlay.get("required_context", []),
    ]
    extension_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        extension_reference,
        *extension_overlay.get("required_context", []),
        *extension_conditional_refs,
    ]
    extension_compact = measure(
        [value for value in extension_compact_refs if value]
    )
    extension_full_reference = measure(
        [value for value in extension_full_reference_refs if value]
    )

    dependency_reference, dependency_overlay = intent_contracts.get(
        "dependency-knowledge-request", (None, {})
    )
    dependency_conditional_refs = [
        entry.get("path")
        for entry in dependency_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    dependency_compact_refs = [
        operation_routing.get("index", ""),
        dependency_reference,
        *dependency_overlay.get("required_context", []),
    ]
    dependency_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        dependency_reference,
        *dependency_overlay.get("required_context", []),
        *dependency_conditional_refs,
    ]
    dependency_compact = measure(
        [value for value in dependency_compact_refs if value]
    )
    dependency_full_reference = measure(
        [value for value in dependency_full_reference_refs if value]
    )

    workspace_mode_reference, workspace_mode_overlay = intent_contracts.get(
        "workspace-mode-request", (None, {})
    )
    workspace_mode_conditional_refs = [
        entry.get("path")
        for entry in workspace_mode_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    workspace_mode_compact_refs = [
        operation_routing.get("index", ""),
        workspace_mode_reference,
        *workspace_mode_overlay.get("required_context", []),
    ]
    workspace_mode_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        workspace_mode_reference,
        *workspace_mode_overlay.get("required_context", []),
        *workspace_mode_conditional_refs,
    ]
    workspace_mode_compact = measure(
        [value for value in workspace_mode_compact_refs if value]
    )
    workspace_mode_full_reference = measure(
        [value for value in workspace_mode_full_reference_refs if value]
    )

    team_reference, team_overlay = task_scale_contracts.get(
        "team-active", (None, {})
    )
    team_conditional_refs = [
        entry.get("path")
        for entry in team_overlay.get("conditional_context", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    ]
    team_compact_refs = [
        operation_routing.get("index", ""),
        team_reference,
        *team_overlay.get("required_context", []),
    ]
    team_full_reference_refs = [
        operation_routing.get("catalog", ""),
        ".ai/assistant/help.md",
        ".ai/assistant/flows/operation-routing.flow.md",
        ".ai/assistant/module-profile.md",
        team_reference,
        *team_overlay.get("required_context", []),
        *team_conditional_refs,
        ".ai/assistant/flows/team-identity.flow.md",
        ".ai/assistant/flows/team-task-coordination.flow.md",
        ".ai/assistant/flows/team-handoff.flow.md",
        ".ai/assistant/flows/team-decision.flow.md",
        ".ai/assistant/flows/team-review.flow.md",
    ]
    team_compact = measure([value for value in team_compact_refs if value])
    team_full_reference = measure(
        [value for value in team_full_reference_refs if value]
    )

    large_reference, large_overlay = task_scale_contracts.get(
        "large-or-resumable", (None, {})
    )
    team_large_composition = measure(
        [
            value
            for value in [
                large_reference,
                *large_overlay.get("required_context", []),
                team_reference,
                *team_overlay.get("required_context", []),
            ]
            if value
        ]
    )

    migration_reference, migration = descriptor(router.get("migration_routing", {}))
    migration_initial_refs = [
        value
        for value in [migration_reference, *migration.get("required_context", [])]
        if value
    ]
    migration_full_refs = list(
        dict.fromkeys(
            [
                *migration_initial_refs,
                *migration.get("candidate_context", []),
            ]
        )
    )
    migration_initial = measure(migration_initial_refs)
    migration_full = measure(migration_full_refs)

    _, cost_scenario_contract = descriptor(router.get("cost_scenarios", {}))
    cost_scenarios: dict[str, dict[str, Any]] = {}
    for name, scenario in cost_scenario_contract.get("scenarios", {}).items():
        if not isinstance(scenario, dict):
            continue
        references: list[str] = []
        profile_name = scenario.get("profile")
        profile_reference, profile_contract = profile_contracts.get(
            profile_name, (None, {})
        )
        references.extend(
            value
            for value in [
                profile_reference,
                *profile_contract.get("required_context", []),
            ]
            if value
        )
        for overlay_name in scenario.get("intent_overlays", []):
            reference, contract = intent_contracts.get(overlay_name, (None, {}))
            references.extend(
                value
                for value in [reference, *contract.get("required_context", [])]
                if value
            )
        for overlay_name in scenario.get("task_scale_overlays", []):
            reference, contract = task_scale_contracts.get(overlay_name, (None, {}))
            references.extend(
                value
                for value in [reference, *contract.get("required_context", [])]
                if value
            )
        scenario_measure = measure(references)
        scenario_measure["expected_budget_state"] = scenario.get(
            "expected_budget_state"
        )
        cost_scenarios[name] = scenario_measure

    return {
        "schema_version": 1,
        "report_kind": "static-target-context-cost",
        "source": "templates/target/.ai/assistant/context-router.json",
        "measurement": "whitespace-delimited words in resolved source templates",
        "budgets": router.get("context_budgets", {}),
        "bootstrap": bootstrap,
        "profiles": profiles,
        "intent_overlays": intent_overlays,
        "task_scale_overlays": task_scale_overlays,
        "task_overlay_compositions": {
            "large-or-resumable+team-active": team_large_composition,
        },
        "cost_scenarios": cost_scenarios,
        "operation_routes": {
            "diagram-discussion": {
                "compact": diagram_compact,
                "full_reference_union": diagram_full_reference,
                "word_reduction_percent": reduction_percent(
                    diagram_compact["words"], diagram_full_reference["words"]
                ),
            },
            "architecture-assistance": {
                "compact": architecture_compact,
                "full_reference_union": architecture_full_reference,
                "word_reduction_percent": reduction_percent(
                    architecture_compact["words"],
                    architecture_full_reference["words"],
                ),
            },
            "code-documentation": {
                "compact": code_documentation_compact,
                "full_reference_union": code_documentation_full_reference,
                "word_reduction_percent": reduction_percent(
                    code_documentation_compact["words"],
                    code_documentation_full_reference["words"],
                ),
            },
            "project-vocabulary": {
                "compact": vocabulary_compact,
                "full_reference_union": vocabulary_full_reference,
                "word_reduction_percent": reduction_percent(
                    vocabulary_compact["words"],
                    vocabulary_full_reference["words"],
                ),
            },
            "test-first-development": {
                "compact": test_first_compact,
                "full_reference_union": test_first_full_reference,
                "word_reduction_percent": reduction_percent(
                    test_first_compact["words"],
                    test_first_full_reference["words"],
                ),
            },
            "extension-management": {
                "compact": extension_compact,
                "full_reference_union": extension_full_reference,
                "word_reduction_percent": reduction_percent(
                    extension_compact["words"],
                    extension_full_reference["words"],
                ),
            },
            "dependency-knowledge": {
                "compact": dependency_compact,
                "full_reference_union": dependency_full_reference,
                "word_reduction_percent": reduction_percent(
                    dependency_compact["words"],
                    dependency_full_reference["words"],
                ),
            },
            "workspace-mode": {
                "compact": workspace_mode_compact,
                "full_reference_union": workspace_mode_full_reference,
                "word_reduction_percent": reduction_percent(
                    workspace_mode_compact["words"],
                    workspace_mode_full_reference["words"],
                ),
            },
            "team-collaboration": {
                "compact": team_compact,
                "full_reference_union": team_full_reference,
                "word_reduction_percent": reduction_percent(
                    team_compact["words"],
                    team_full_reference["words"],
                ),
            },
        },
        "migration_routing": {
            "initial": migration_initial,
            "full_candidate_union": migration_full,
            "initial_word_reduction_percent": reduction_percent(
                migration_initial["words"], migration_full["words"]
            ),
        },
        "limitations": [
            "token count uses a four-characters-per-token estimate, not model billing",
            "runtime clients may preload hidden context not represented by repository paths",
            "placeholder target-owned context is unresolved",
            "runtime expansion depends on task evidence",
        ],
    }


def build_installed_report(target: Path) -> dict[str, Any]:
    target = target.resolve()
    router_path = target / ".ai" / "assistant" / "context-router.json"
    router = json.loads(router_path.read_text(encoding="utf-8"))
    if not isinstance(router, dict):
        raise ValueError("installed context router must contain an object")
    bootstrap = measure_installed(
        target,
        [
            *router.get("preloaded_context", []),
            *router.get("bootstrap_context", []),
        ],
    )
    profiles: dict[str, dict[str, Any]] = {}
    for name, entry in router.get("profile_index", {}).items():
        if not isinstance(entry, dict) or not isinstance(entry.get("descriptor"), str):
            continue
        reference = entry["descriptor"]
        descriptor_path = installed_path(target, reference)
        descriptor_data: dict[str, Any] = {}
        if descriptor_path and descriptor_path.is_file():
            loaded = json.loads(descriptor_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                descriptor_data = loaded
        profiles[name] = measure_installed(
            target,
            [reference, *descriptor_data.get("required_context", [])],
        )
    return {
        "schema_version": 1,
        "report_kind": "installed-target-context-cost",
        "target": str(target),
        "budgets": router.get("context_budgets", {}),
        "bootstrap": bootstrap,
        "profiles": profiles,
        "limitations": [
            "word counts measure repository files, not hidden client context or billed tokens",
            "conditional context is measured only when selected for a concrete task",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure deterministic context costs from the target router template."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    report = build_installed_report(args.target) if args.target else build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
