#!/usr/bin/env python3
"""Run the stable AlatyrCore source-repository checks.

This helper validates this source repository only. It is not a portable
framework requirement for target projects.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ["tools/check_framework_metadata.py"],
    ["tools/check_approval_template.py"],
    ["tools/check_ai_infrastructure_inventory.py"],
    ["tools/check_ai_infrastructure_router.py"],
    ["tools/check_assistant_surface_conformance.py"],
    ["tools/check_bridge_capability_matrix.py"],
    ["tools/check_context_router.py"],
    ["tools/check_context_costs.py"],
    ["tools/check_consistency_map.py"],
    ["tools/check_cross_platform_tools.py"],
    ["tools/check_large_task_orchestration.py"],
    ["tools/check_manifest_contract.py"],
    ["tools/check_markdown_links.py"],
    ["tools/check_maturity_profile.py"],
    ["tools/check_module_profile.py"],
    ["tools/check_migration_diff_report.py"],
    ["tools/check_operation_contracts.py"],
    ["tools/check_operation_help.py"],
    ["tools/check_output_contracts.py"],
    ["tools/check_release_migration_template.py"],
    ["tools/check_rule_ownership.py"],
    ["tools/check_source_of_truth_registry.py"],
    ["tools/check_target_adapter_validator.py"],
    ["tools/check_versioning.py"],
    ["tools/check_bridge_templates.py"],
    ["tools/render_bridge_templates.py"],
    ["tools/check_conformance_fixtures.py"],
    ["tools/check_conformance_reports.py"],
    ["tools/check_conformance_summary.py"],
    ["tools/run_conformance_scaffold.py"],
    [
        "tools/report_migration_diff.py",
        "--from-rules",
        "framework/rule-registry.json",
    ],
    [
        "tools/summarize_effectiveness_reports.py",
        "--input",
        "conformance/golden/effectiveness-sample.json",
    ],
    ["tools/check_framework_consistency.py"],
]


def run_check(command: list[str]) -> int:
    full_command = [sys.executable, *command]
    print("$ " + " ".join(full_command), flush=True)
    result = subprocess.run(full_command, cwd=ROOT, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run stable AlatyrCore source-repository validation checks."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List checks without running them.",
    )
    args = parser.parse_args()

    if args.list:
        for command in CHECKS:
            print(" ".join([sys.executable, *command]))
        return 0

    failures: list[str] = []
    for command in CHECKS:
        if run_check(command) != 0:
            failures.append(" ".join(command))

    if failures:
        print("\nFAILED source checks:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nOK: ran {len(CHECKS)} source checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
