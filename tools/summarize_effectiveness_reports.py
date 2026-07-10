#!/usr/bin/env python3
"""Summarize Alatyr effectiveness report data.

This is a source-repository helper for pilots and conformance work. It is not
a portable validation requirement for target projects.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "task",
    "task_profile",
    "adapter_mode",
    "operation_id",
    "context_files_loaded",
    "approximate_context_volume",
    "clarifications",
    "approvals_requested",
    "validation",
    "hallucinated_commands",
    "missed_companion_updates",
    "rework_count",
    "protected_changes_blocked",
    "residual_risks",
    "outcome",
]

ADAPTER_MODES = {"none", "minimal", "full"}
OUTCOMES = {"accepted", "rework", "blocked"}
COUNT_FIELDS = [
    "context_files_loaded",
    "approximate_context_volume",
    "clarifications",
    "approvals_requested",
    "missed_companion_updates",
    "rework_count",
    "protected_changes_blocked",
]


def load_reports(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path} is empty")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        reports: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            reports.append(item)
        return reports

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError(f"{path} must contain a JSON object, array, or JSON lines")


def validate_report(report: dict[str, Any], index: int) -> list[str]:
    failures: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in report:
            failures.append(f"report {index} missing {field}")

    adapter_mode = report.get("adapter_mode")
    if adapter_mode not in ADAPTER_MODES:
        failures.append(
            f"report {index} adapter_mode must be one of {sorted(ADAPTER_MODES)}"
        )

    outcome = report.get("outcome")
    if outcome not in OUTCOMES:
        failures.append(f"report {index} outcome must be one of {sorted(OUTCOMES)}")

    for field in COUNT_FIELDS:
        value = report.get(field)
        if value == "unknown":
            continue
        if not isinstance(value, int) or value < 0:
            failures.append(f"report {index} {field} must be a non-negative int or unknown")

    for field in [
        "task",
        "task_profile",
        "operation_id",
        "validation",
        "hallucinated_commands",
        "residual_risks",
    ]:
        value = report.get(field)
        if not isinstance(value, str) or not value:
            failures.append(f"report {index} {field} must be a non-empty string")

    return failures


def average_known(values: list[int]) -> str:
    if not values:
        return "unknown"
    return f"{sum(values) / len(values):.2f}"


def render_summary(reports: list[dict[str, Any]]) -> str:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        by_mode[report["adapter_mode"]].append(report)
        by_profile[report["task_profile"]].append(report)

    lines = [f"OK: loaded {len(reports)} effectiveness reports", ""]
    for mode in sorted(by_mode):
        mode_reports = by_mode[mode]
        outcomes = Counter(report["outcome"] for report in mode_reports)
        lines.extend(
            [
                f"Adapter mode: `{mode}`",
                f"- reports: {len(mode_reports)}",
                f"- accepted: {outcomes.get('accepted', 0)}",
                f"- rework: {outcomes.get('rework', 0)}",
                f"- blocked: {outcomes.get('blocked', 0)}",
            ]
        )
        for field in COUNT_FIELDS:
            known_values = [
                report[field]
                for report in mode_reports
                if isinstance(report.get(field), int)
            ]
            lines.append(f"- average {field}: {average_known(known_values)}")
        lines.append("")
    lines.extend(["Task profiles:", ""])
    for profile in sorted(by_profile):
        lines.append(f"- `{profile}`: {len(by_profile[profile])}")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and summarize Alatyr effectiveness report data."
    )
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    try:
        reports = load_reports(args.input)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for index, report in enumerate(reports, start=1):
        failures.extend(validate_report(report, index))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(render_summary(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
