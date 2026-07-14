#!/usr/bin/env python3
"""Summarize captured assistant-run conformance reports.

This source-repository helper reads actual assistant-run JSON reports that
were already captured. It does not run an assistant, install Alatyr, or
validate a target project.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from check_conformance_reports import (
    FIXTURES,
    SHARED,
    load_json,
    validate_actual_reports,
)
from check_conformance_matrix import safe_relative_path, validate_matrix


def fixture_names() -> list[str]:
    return sorted(path.name for path in FIXTURES.iterdir() if path.is_dir())


def report_paths(actual_dirs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for actual_dir in actual_dirs:
        paths.extend(sorted(path for path in actual_dir.glob("*.json") if path.is_file()))
    return paths


def load_reports(actual_dirs: list[Path]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in report_paths(actual_dirs):
        report = load_json(path)
        report["_report_path"] = path.as_posix()
        reports.append(report)
    return reports


def average(values: list[int]) -> str:
    if not values:
        return "unknown"
    return f"{sum(values) / len(values):.2f}"


def summarize_reports(reports: list[dict[str, Any]]) -> str:
    all_fixtures = set(fixture_names())
    by_surface: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_fixture: dict[str, list[dict[str, Any]]] = defaultdict(list)
    risk_counter: Counter[str] = Counter()
    unresolved_counter: Counter[str] = Counter()
    adapter_evidence_counters: dict[str, Counter[str]] = {
        "operation_help_status": Counter(),
        "output_contract_status": Counter(),
        "ai_infrastructure_inventory_status": Counter(),
    }

    for report in reports:
        surface = str(report["assistant_surface"])
        fixture = str(report["fixture"])
        by_surface[surface].append(report)
        by_fixture[fixture].append(report)
        for risk in report.get("residual_risk", []):
            risk_counter[str(risk)] += 1
        validation_status = report.get("validation_status", {})
        if isinstance(validation_status, dict):
            for unresolved in validation_status.get("unresolved", []):
                unresolved_counter[str(unresolved)] += 1
        for field, counter in adapter_evidence_counters.items():
            for item in report.get(field, []):
                counter[str(item)] += 1

    lines = [
        "# Alatyr Assistant-Run Conformance Summary",
        "",
        f"Reports loaded: {len(reports)}",
        f"Assistant surfaces: {len(by_surface)}",
        f"Fixtures covered: {len(by_fixture)} of {len(all_fixtures)}",
        "",
        "## Surface Coverage",
        "",
    ]

    for surface in sorted(by_surface):
        surface_reports = by_surface[surface]
        covered = sorted(str(report["fixture"]) for report in surface_reports)
        missing = sorted(all_fixtures - set(covered))
        run_ids = sorted({str(report["run_id"]) for report in surface_reports})
        commits = sorted({str(report["source_commit"]) for report in surface_reports})
        loaded_counts = [
            evidence["loaded_file_count"]
            for report in surface_reports
            for evidence in [report.get("context_cost_evidence", {})]
            if isinstance(evidence, dict)
            and isinstance(evidence.get("loaded_file_count"), int)
        ]
        word_counts = [
            evidence["approximate_words"]
            for report in surface_reports
            for evidence in [report.get("context_cost_evidence", {})]
            if isinstance(evidence, dict)
            and isinstance(evidence.get("approximate_words"), int)
        ]
        budget_exceeded = sum(
            1
            for report in surface_reports
            if report.get("context_cost_evidence", {}).get("budget_exceeded") is True
        )
        changed_facts = sum(
            len(report.get("logical_integrity_evidence", {}).get("changed_fact_ids", []))
            for report in surface_reports
        )
        selected_relationships = sum(
            len(
                report.get("logical_integrity_evidence", {}).get(
                    "selected_relationships", []
                )
            )
            for report in surface_reports
        )
        companion_surfaces = sum(
            len(
                report.get("logical_integrity_evidence", {}).get(
                    "companion_surfaces_checked", []
                )
            )
            for report in surface_reports
        )
        lines.extend(
            [
                f"- Surface: `{surface}`",
                f"  Reports: {len(surface_reports)}",
                f"  Fixtures: {', '.join(f'`{item}`' for item in covered) or 'none'}",
                f"  Missing fixtures: {', '.join(f'`{item}`' for item in missing) or 'none'}",
                f"  Run ids: {', '.join(f'`{item}`' for item in run_ids)}",
                f"  Source commits: {', '.join(f'`{item}`' for item in commits)}",
                f"  Average loaded files: {average(loaded_counts)}",
                f"  Average approximate words: {average(word_counts)}",
                f"  Context budget exceeded: {budget_exceeded}",
                f"  Changed fact evidence items: {changed_facts}",
                f"  Selected relationship evidence items: {selected_relationships}",
                f"  Companion surface evidence items: {companion_surfaces}",
            ]
        )

    lines.extend(["", "## Fixture Coverage", ""])
    for fixture in sorted(all_fixtures):
        fixture_reports = by_fixture.get(fixture, [])
        surfaces = sorted(str(report["assistant_surface"]) for report in fixture_reports)
        lines.extend(
            [
                f"- Fixture: `{fixture}`",
                f"  Reports: {len(fixture_reports)}",
                f"  Surfaces: {', '.join(f'`{item}`' for item in surfaces) or 'none'}",
            ]
        )

    lines.extend(["", "## Residual Risk Counts", ""])
    if risk_counter:
        for risk, count in sorted(risk_counter.items()):
            lines.append(f"- `{risk}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Unresolved Validation Counts", ""])
    if unresolved_counter:
        for unresolved, count in sorted(unresolved_counter.items()):
            lines.append(f"- `{unresolved}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Adapter Evidence Counts", ""])
    for field, counter in adapter_evidence_counters.items():
        lines.append(f"Field: `{field}`")
        if counter:
            for item, count in sorted(counter.items()):
                lines.append(f"- `{item}`: {count}")
        else:
            lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "This summary only compares captured conformance reports. It does not "
            "run an assistant, prove target validation, or complete an installation.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize captured assistant-run conformance reports."
    )
    parser.add_argument(
        "--actual-dir",
        action="append",
        default=[],
        type=Path,
        help="Directory containing assistant-run JSON reports. May be repeated.",
    )
    parser.add_argument(
        "--matrix",
        action="append",
        default=[],
        type=Path,
        help="Prepared matrix.json containing captured reports. May be repeated.",
    )
    parser.add_argument(
        "--require-all-fixtures",
        action="store_true",
        help="Require each actual report directory to cover every fixture.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    try:
        if not args.actual_dir and not args.matrix:
            failures.append("provide --actual-dir or --matrix")
        actual_dirs = list(args.actual_dir)
        for matrix_path in args.matrix:
            failures.extend(validate_matrix(matrix_path, require_reports=True))
            matrix = load_json(matrix_path)
            base = matrix_path.resolve().parent
            for run in matrix.get("runs", []):
                if isinstance(run, dict):
                    actual_dirs.append(
                        safe_relative_path(
                            base,
                            run.get("reports_directory"),
                            "reports_directory",
                        )
                    )
        shared = load_json(SHARED)
        for actual_dir in args.actual_dir:
            failures.extend(
                validate_actual_reports(
                    actual_dir,
                    shared,
                    require_reports=True,
                    require_all_fixtures=args.require_all_fixtures,
                )
            )
        if not failures:
            reports = load_reports(actual_dirs)
            print(summarize_reports(reports), end="")
    except (OSError, ValueError, AssertionError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
