#!/usr/bin/env python3
"""Summarize reviewed no/minimal/full effectiveness benchmark reports."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from check_effectiveness_benchmark import validate_benchmark
from prepare_effectiveness_benchmark import MODES, load_json


METRICS = [
    "input_tokens",
    "output_tokens",
    "estimated_cost",
    "context_files_loaded",
    "approximate_context_volume",
    "context_expansions",
    "clarifications",
    "approvals_requested",
    "hallucinated_command_count",
    "validation_error_count",
    "missed_companion_updates",
    "rework_count",
    "changed_fact_count",
    "relationships_reviewed",
    "companion_surfaces_checked",
    "unresolved_consistency_gaps",
    "duration_seconds",
    "protected_changes_blocked",
]


def mean(reports: list[dict[str, Any]], field: str) -> float | None:
    values = [
        report[field]
        for report in reports
        if isinstance(report.get(field), (int, float))
        and not isinstance(report.get(field), bool)
    ]
    if len(values) != len(reports) or not values:
        return None
    return sum(values) / len(values)


def rendered(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.2f}"


def reduction(reference: float | None, candidate: float | None) -> str:
    if reference is None or candidate is None or reference == 0:
        return "not-computable"
    return f"{(1 - candidate / reference) * 100:.1f}%"


def render_summary(manifest: dict[str, Any], reports: list[dict[str, Any]]) -> str:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        by_mode[report["adapter_mode"]].append(report)
    measurements = {report["context_measurement_kind"] for report in reports}
    context_ready = (
        len(measurements) == 1
        and "unknown" not in measurements
        and all(isinstance(report.get("approximate_context_volume"), int) for report in reports)
    )
    token_ready = all(
        isinstance(report.get(field), int)
        for report in reports
        for field in ["input_tokens", "output_tokens"]
    )
    currencies = {report["cost_currency"] for report in reports}
    cost_sources = {report["cost_evidence"] for report in reports}
    monetary_ready = (
        len(currencies) == 1
        and "unknown" not in currencies
        and len(cost_sources) == 1
        and "unknown" not in cost_sources
        and all(
            isinstance(report.get("estimated_cost"), (int, float))
            and not isinstance(report.get("estimated_cost"), bool)
            for report in reports
        )
    )
    timing_ready = all(isinstance(report.get("duration_seconds"), int) for report in reports)
    lines = [
        "# Alatyr Effectiveness Benchmark Summary",
        "",
        f"Benchmark: `{manifest['benchmark_id']}`",
        f"Source commit: `{manifest['source_commit']}`",
        f"Tasks: {len(manifest['tasks'])}",
        f"Repetitions: {manifest['repetitions']}",
        f"Reviewed reports: {len(reports)} of {manifest['expected_report_count']}",
        f"Comparable context-cost evidence: {'yes' if context_ready else 'no'}",
        f"Comparable token evidence: {'yes' if token_ready else 'no'}",
        f"Comparable monetary-cost evidence: {'yes' if monetary_ready else 'no'}",
        f"Comparable timing evidence: {'yes' if timing_ready else 'no'}",
        "",
        "## Adapter Modes",
        "",
    ]
    mode_means: dict[str, dict[str, float | None]] = {}
    for mode in MODES:
        mode_reports = by_mode.get(mode, [])
        mode_means[mode] = {field: mean(mode_reports, field) for field in METRICS}
        outcomes = Counter(report["outcome"] for report in mode_reports)
        criteria = Counter(
            result["status"]
            for report in mode_reports
            for result in report["acceptance_criteria_results"]
        )
        lines.extend(
            [
                f"Mode: `{mode}`",
                f"- Reports: {len(mode_reports)}",
                f"- Accepted/rework/blocked: {outcomes['accepted']}/{outcomes['rework']}/{outcomes['blocked']}",
                f"- Criteria pass/fail/unresolved: {criteria['pass']}/{criteria['fail']}/{criteria['unresolved']}",
            ]
        )
        for field in METRICS:
            lines.append(f"- Average {field}: {rendered(mode_means[mode][field])}")
        lines.append("")

    lines.extend(["## Relative To None", ""])
    reference = mode_means["none"]
    for mode in ["minimal", "full"]:
        values = mode_means[mode]
        reference_tokens = None
        candidate_tokens = None
        if reference["input_tokens"] is not None and reference["output_tokens"] is not None:
            reference_tokens = reference["input_tokens"] + reference["output_tokens"]
        if values["input_tokens"] is not None and values["output_tokens"] is not None:
            candidate_tokens = values["input_tokens"] + values["output_tokens"]
        lines.extend(
            [
                f"Mode: `{mode}`",
                "- Total-token reduction: "
                + reduction(reference_tokens, candidate_tokens),
                "- Estimated-cost reduction: "
                + reduction(reference["estimated_cost"], values["estimated_cost"]),
                "- Context-volume reduction: "
                + reduction(
                    reference["approximate_context_volume"],
                    values["approximate_context_volume"],
                ),
                "- Loaded-file reduction: "
                + reduction(reference["context_files_loaded"], values["context_files_loaded"]),
                "- Duration reduction: "
                + reduction(reference["duration_seconds"], values["duration_seconds"]),
                "- Rework reduction: "
                + reduction(reference["rework_count"], values["rework_count"]),
                "- Unresolved-gap reduction: "
                + reduction(
                    reference["unresolved_consistency_gaps"],
                    values["unresolved_consistency_gaps"],
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "Negative reductions mean the adapter mode used more of that metric than "
            "the no-adapter mode. `not-computable` means evidence was unknown or the "
            "reference was zero. This summary reports reviewed measurements; it does "
            "not by itself prove broad cost or quality improvement.",
        ]
    )
    return "\n".join(lines) + "\n"


def source_self_check() -> list[str]:
    reports: list[dict[str, Any]] = []
    for index, mode in enumerate(MODES, start=1):
        reports.append(
            {
                "adapter_mode": mode,
                "outcome": "accepted",
                "context_measurement_kind": "host-observed-tokens",
                "input_tokens": index * 80,
                "output_tokens": index * 20,
                "estimated_cost": index * 0.01,
                "cost_currency": "USD",
                "cost_evidence": "synthetic billing estimate",
                "context_files_loaded": index,
                "approximate_context_volume": index * 100,
                "context_expansions": 0,
                "clarifications": 0,
                "approvals_requested": 0,
                "hallucinated_command_count": 0,
                "validation_error_count": 0,
                "missed_companion_updates": 0,
                "rework_count": index - 1,
                "changed_fact_count": 1,
                "relationships_reviewed": index,
                "companion_surfaces_checked": index,
                "unresolved_consistency_gaps": 0,
                "duration_seconds": index * 10,
                "protected_changes_blocked": 0,
                "acceptance_criteria_results": [
                    {"status": "pass"}
                ],
            }
        )
    manifest = {
        "benchmark_id": "summary-source-check",
        "source_commit": "source-contract",
        "tasks": [{"id": "task"}],
        "repetitions": 1,
        "expected_report_count": 3,
    }
    summary = render_summary(manifest, reports)
    failures: list[str] = []
    for required in [
        "Reviewed reports: 3 of 3",
        "Comparable context-cost evidence: yes",
        "Comparable token evidence: yes",
        "Comparable monetary-cost evidence: yes",
        "Total-token reduction: -100.0%",
        "Context-volume reduction: -100.0%",
        "Negative reductions mean",
    ]:
        if required not in summary:
            failures.append(f"effectiveness benchmark summary missing {required}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize a complete independently reviewed effectiveness benchmark."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        help="Path to benchmark.json. Omit for the source self-check.",
    )
    args = parser.parse_args()
    if args.benchmark is None:
        failures = source_self_check()
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}", file=sys.stderr)
            return 1
        print("OK: checked effectiveness benchmark summary contracts")
        return 0

    failures, reports = validate_benchmark(
        args.benchmark,
        require_reports=True,
        require_reviewed=True,
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    manifest = load_json(args.benchmark)
    print(render_summary(manifest, reports), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
