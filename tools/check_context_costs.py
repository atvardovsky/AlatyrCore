#!/usr/bin/env python3
"""Validate deterministic context-cost baselines and routing budgets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from report_context_costs import build_report


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "conformance" / "golden" / "context-cost-baseline.json"


def main() -> int:
    failures: list[str] = []
    report = build_report()
    try:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: invalid context-cost baseline: {exc}", file=sys.stderr)
        return 1
    if report != baseline:
        failures.append(
            "context-cost baseline drifted; review costs and refresh the golden report"
        )

    bootstrap = report["bootstrap"]
    bootstrap_budget = report["budgets"]["bootstrap"]
    if bootstrap["declared_files"] > bootstrap_budget["max_files"]:
        failures.append("bootstrap declared file count exceeds its budget")
    if bootstrap["words"] > bootstrap_budget["max_words"]:
        failures.append("bootstrap word count exceeds its budget")
    if bootstrap["words"] > bootstrap_budget["soft_max_words"]:
        failures.append("bootstrap word count exceeds its soft headroom budget")

    profile_budget = report["budgets"]["profile_default"]
    max_total_words = profile_budget["max_total_words"]
    max_portable_words = profile_budget["max_portable_words"]
    reserved_target_words = profile_budget["reserved_target_words"]
    if max_portable_words + reserved_target_words > max_total_words:
        failures.append("profile portable and target budgets exceed total budget")
    for name, profile in report["profiles"].items():
        if profile["declared_files"] > profile_budget["max_files"]:
            failures.append(f"profile {name} exceeds the default file budget")
        if profile["words"] > max_portable_words:
            failures.append(f"profile {name} exceeds the portable word budget")
        if profile["missing_paths"]:
            failures.append(f"profile {name} contains missing paths")

    for name, overlay in report["intent_overlays"].items():
        if overlay["declared_files"] > profile_budget["max_files"]:
            failures.append(f"intent overlay {name} exceeds the default file budget")
        if overlay["words"] > max_total_words:
            failures.append(f"intent overlay {name} exceeds the default word budget")
        if overlay["missing_paths"]:
            failures.append(f"intent overlay {name} contains missing paths")

    for name, overlay in report["task_scale_overlays"].items():
        if overlay["declared_files"] > profile_budget["max_files"]:
            failures.append(f"task-scale overlay {name} exceeds the default file budget")
        if overlay["words"] > max_total_words:
            failures.append(f"task-scale overlay {name} exceeds the default word budget")
        if overlay["missing_paths"]:
            failures.append(f"task-scale overlay {name} contains missing paths")

    diagram_route = report["operation_routes"]["diagram-discussion"]
    if diagram_route["compact"]["missing_paths"]:
        failures.append("diagram compact route contains missing paths")
    diagram_reduction = diagram_route["word_reduction_percent"]
    if not isinstance(diagram_reduction, (int, float)) or diagram_reduction < 40:
        failures.append(
            "diagram compact route should reduce reference words by at least 40%"
        )

    architecture_route = report["operation_routes"]["architecture-assistance"]
    if architecture_route["compact"]["missing_paths"]:
        failures.append("architecture compact route contains missing paths")
    architecture_reduction = architecture_route["word_reduction_percent"]
    if not isinstance(architecture_reduction, (int, float)) or architecture_reduction < 35:
        failures.append(
            "architecture compact route should reduce reference words by at least 35%"
        )

    code_documentation_route = report["operation_routes"]["code-documentation"]
    if code_documentation_route["compact"]["missing_paths"]:
        failures.append("code-documentation compact route contains missing paths")
    code_documentation_reduction = code_documentation_route["word_reduction_percent"]
    if (
        not isinstance(code_documentation_reduction, (int, float))
        or code_documentation_reduction < 25
    ):
        failures.append(
            "code-documentation compact route should reduce reference words by at least 25%"
        )

    vocabulary_route = report["operation_routes"]["project-vocabulary"]
    if vocabulary_route["compact"]["missing_paths"]:
        failures.append("project-vocabulary compact route contains missing paths")
    vocabulary_reduction = vocabulary_route["word_reduction_percent"]
    if not isinstance(vocabulary_reduction, (int, float)) or vocabulary_reduction < 25:
        failures.append(
            "project-vocabulary compact route should reduce reference words by at least 25%"
        )

    test_first_route = report["operation_routes"]["test-first-development"]
    if test_first_route["compact"]["missing_paths"]:
        failures.append("test-first compact route contains missing paths")
    test_first_reduction = test_first_route["word_reduction_percent"]
    if not isinstance(test_first_reduction, (int, float)) or test_first_reduction < 25:
        failures.append(
            "test-first compact route should reduce reference words by at least 25%"
        )

    extension_route = report["operation_routes"]["extension-management"]
    if extension_route["compact"]["missing_paths"]:
        failures.append("extension compact route contains missing paths")
    extension_reduction = extension_route["word_reduction_percent"]
    if not isinstance(extension_reduction, (int, float)) or extension_reduction < 25:
        failures.append(
            "extension compact route should reduce reference words by at least 25%"
        )

    team_route = report["operation_routes"]["team-collaboration"]
    if team_route["compact"]["missing_paths"]:
        failures.append("team compact route contains missing paths")
    team_reduction = team_route["word_reduction_percent"]
    if not isinstance(team_reduction, (int, float)) or team_reduction < 50:
        failures.append(
            "team compact preflight should reduce reference words by at least 50%"
        )
    team_composition = report["task_overlay_compositions"][
        "large-or-resumable+team-active"
    ]
    if team_composition["missing_paths"]:
        failures.append("large-task and team composition contains missing paths")
    if team_composition["words"] > max_total_words:
        failures.append("large-task and team compact composition exceeds profile budget")

    for name, scenario in report["cost_scenarios"].items():
        expected = scenario.get("expected_budget_state")
        if expected == "compact":
            if scenario["declared_files"] > profile_budget["max_files"]:
                failures.append(f"compact cost scenario {name} exceeds the file budget")
            if scenario["words"] > max_portable_words:
                failures.append(f"compact cost scenario {name} exceeds the portable budget")
        elif expected == "expansion-receipt-required":
            if scenario["words"] <= 0:
                failures.append(f"expansion cost scenario {name} has no measured context")
        else:
            failures.append(f"cost scenario {name} has no valid expected budget state")

    migration = report["migration_routing"]
    reduction = migration["initial_word_reduction_percent"]
    if not isinstance(reduction, (int, float)) or reduction < 70:
        failures.append("migration-first routing should reduce initial words by at least 70%")
    if migration["initial"]["declared_files"] > 8:
        failures.append("migration-first initial context exceeds eight files")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: checked context-cost baseline; migration initial word reduction "
        f"is {reduction}%; diagram route reduction is {diagram_reduction}%; "
        f"architecture route reduction is {architecture_reduction}%"
        f"; code-documentation route reduction is {code_documentation_reduction}%"
        f"; project-vocabulary route reduction is {vocabulary_reduction}%"
        f"; test-first route reduction is {test_first_reduction}%"
        f"; extension route reduction is {extension_reduction}%"
        f"; team preflight reduction is {team_reduction}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
