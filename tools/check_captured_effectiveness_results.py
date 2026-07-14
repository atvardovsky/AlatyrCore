#!/usr/bin/env python3
"""Validate compact committed effectiveness benchmark evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from check_effectiveness_benchmark import MODES, validate_benchmark_report


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "conformance" / "benchmarks" / "results"
HEX = set("0123456789abcdef")


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return data


def safe_child(base: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"{base} missing {field}")
    relpath = Path(value)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise AssertionError(f"{base} has unsafe {field}: {value}")
    path = base / relpath
    if not path.is_file():
        raise AssertionError(f"{base} {field} does not exist: {value}")
    return path


def sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def validate_result(path: Path) -> None:
    result = load(path)
    base = path.parent
    if result.get("schema_version") != 1:
        raise AssertionError(f"{path} schema_version must be 1")
    if result.get("result_kind") != "captured-effectiveness-benchmark":
        raise AssertionError(f"{path} result_kind is invalid")
    for field in ["benchmark_id", "source_commit"]:
        if not isinstance(result.get(field), str) or not result[field]:
            raise AssertionError(f"{path} missing {field}")
    if not sha256(result.get("input_plan_hash")):
        raise AssertionError(f"{path} input_plan_hash must be sha256")

    task = result.get("task")
    if not isinstance(task, dict):
        raise AssertionError(f"{path} task must be an object")
    criteria = task.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise AssertionError(f"{path} task acceptance criteria are missing")
    reports = result.get("reports")
    if not isinstance(reports, dict) or list(reports) != MODES:
        raise AssertionError(f"{path} reports must preserve none/minimal/full order")

    execution_path = safe_child(base, result.get("execution_summary"), "execution_summary")
    review_path = safe_child(base, result.get("review_evidence"), "review_evidence")
    safe_child(base, result.get("summary"), "summary")
    execution = load(execution_path)
    review = load(review_path)
    if execution.get("benchmark_id") != result["benchmark_id"]:
        raise AssertionError(f"{execution_path} benchmark_id drifted")
    executions = execution.get("executions")
    if not isinstance(executions, list) or len(executions) != len(MODES):
        raise AssertionError(f"{execution_path} must contain three executions")
    execution_by_mode = {item.get("adapter_mode"): item for item in executions}
    if set(execution_by_mode) != set(MODES):
        raise AssertionError(f"{execution_path} mode coverage drifted")

    manifest = {
        "benchmark_id": result["benchmark_id"],
        "source_commit": result["source_commit"],
    }
    for mode, report_relpath in reports.items():
        report_path = safe_child(base, report_relpath, f"report {mode}")
        report = load(report_path)
        run = {
            "task_id": task["id"],
            "adapter_mode": mode,
            "run_id": report.get("operation_id"),
            "repetition": task["repetition"],
            "project_baseline_hash": task["project_baseline_hash"],
        }
        validate_benchmark_report(
            report_path,
            report,
            manifest,
            run,
            task,
            require_reviewed=True,
        )
        observed = execution_by_mode[mode]
        usage = observed.get("usage")
        if not isinstance(usage, dict):
            raise AssertionError(f"{execution_path} {mode} usage is missing")
        if report.get("input_tokens") != usage.get("input_tokens"):
            raise AssertionError(f"{report_path} input token evidence drifted")
        if report.get("output_tokens") != usage.get("output_tokens"):
            raise AssertionError(f"{report_path} output token evidence drifted")
        if observed.get("exit_code") != 0 or observed.get("report_exists") is not True:
            raise AssertionError(f"{execution_path} {mode} did not complete cleanly")

    if review.get("evidence_kind") != "independent-benchmark-review":
        raise AssertionError(f"{review_path} review kind is invalid")
    for field in [
        "readme_result_sha256",
        "package_baseline_and_result_sha256",
        "ui_source_baseline_and_result_sha256",
    ]:
        if not sha256(review.get(field)):
            raise AssertionError(f"{review_path} {field} must be sha256")
    if review.get("verified_modes") != MODES:
        raise AssertionError(f"{review_path} verified mode coverage drifted")
    claims = result.get("claims")
    if not isinstance(claims, dict) or claims.get("broad_cost_claim_supported") is not False:
        raise AssertionError(f"{path} must preserve the narrow interpretation boundary")


def main() -> int:
    failures: list[str] = []
    result_paths = sorted(RESULTS.glob("*/result.json"))
    if not result_paths:
        failures.append("no captured effectiveness result manifests found")
    for path in result_paths:
        try:
            validate_result(path)
        except (OSError, json.JSONDecodeError, AssertionError, KeyError) as exc:
            failures.append(str(exc))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: checked {len(result_paths)} captured effectiveness benchmark(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
