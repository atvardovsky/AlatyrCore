#!/usr/bin/env python3
"""Validate paired effectiveness benchmark plans and captured reports."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from prepare_effectiveness_benchmark import (
    MODES,
    REPORT_TEMPLATE,
    adapter_pattern_allowed,
    load_json,
    prepare_benchmark,
    tree_hash,
)
from summarize_effectiveness_reports import validate_report as validate_metrics


ROOT = Path(__file__).resolve().parents[1]
PLAN_TEMPLATE = ROOT / "conformance" / "benchmarks" / "benchmark-plan-template.json"
HEX = set("0123456789abcdef")


def is_placeholder(value: str) -> bool:
    return value.startswith("{") and value.endswith("}")


def safe_path(base: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"benchmark {field} must be a non-empty relative path")
    relpath = Path(value)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise AssertionError(f"benchmark {field} is unsafe: {value}")
    return base / relpath


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def validate_provenance(value: Any, path: Path) -> None:
    if not isinstance(value, dict):
        raise AssertionError(f"{path} run_provenance must be an object")
    for field in [
        "provider",
        "product",
        "model",
        "version_or_date",
        "execution_mode",
        "started_at",
        "completed_at",
        "operator",
        "report_origin",
    ]:
        item = value.get(field)
        if not isinstance(item, str) or not item or is_placeholder(item):
            raise AssertionError(f"{path} run_provenance.{field} must be recorded")


def task_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise AssertionError("benchmark tasks must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise AssertionError("benchmark task entries must be objects")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in result:
            raise AssertionError("benchmark task ids must be unique strings")
        criteria = task.get("acceptance_criteria")
        if not isinstance(criteria, list) or not criteria or not all(
            isinstance(item, str) and item for item in criteria
        ):
            raise AssertionError(f"benchmark task {task_id} has invalid criteria")
        for field in ["name", "task_profile", "allowed_actions"]:
            if not isinstance(task.get(field), str) or not task[field]:
                raise AssertionError(f"benchmark task {task_id} has invalid {field}")
        if not valid_sha256(task.get("project_baseline_hash")):
            raise AssertionError(f"benchmark task {task_id} has invalid baseline hash")
        hashes = task.get("mode_snapshot_hashes")
        if not isinstance(hashes, dict) or set(hashes) != set(MODES) or not all(
            valid_sha256(value) for value in hashes.values()
        ):
            raise AssertionError(f"benchmark task {task_id} has invalid mode hashes")
        result[task_id] = task
    return result


def validate_acceptance_results(
    report: dict[str, Any],
    task: dict[str, Any],
    report_path: Path,
) -> None:
    results = report.get("acceptance_criteria_results")
    if not isinstance(results, list) or len(results) != len(task["acceptance_criteria"]):
        raise AssertionError(f"{report_path} acceptance result count drifted")
    seen: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            raise AssertionError(f"{report_path} acceptance results must be objects")
        criterion = result.get("criterion")
        if criterion not in task["acceptance_criteria"] or criterion in seen:
            raise AssertionError(f"{report_path} acceptance criterion drifted")
        seen.add(criterion)
        if result.get("status") not in {"pass", "fail", "unresolved"}:
            raise AssertionError(f"{report_path} acceptance status is invalid")
        evidence = result.get("evidence")
        if not isinstance(evidence, str) or not evidence or is_placeholder(evidence):
            raise AssertionError(f"{report_path} acceptance evidence is missing")


def validate_review(
    report: dict[str, Any],
    report_path: Path,
    *,
    require_reviewed: bool,
) -> None:
    review = report.get("review")
    if not isinstance(review, dict) or review.get("status") not in {"pending", "reviewed"}:
        raise AssertionError(f"{report_path} review status must be pending or reviewed")
    for field in ["reviewer", "reviewed_at", "notes"]:
        value = review.get(field)
        if not isinstance(value, str) or not value or is_placeholder(value):
            raise AssertionError(f"{report_path} review.{field} must be recorded")
    if require_reviewed:
        if review["status"] != "reviewed":
            raise AssertionError(f"{report_path} requires independent review")
        if review["reviewer"] == "unknown" or review["reviewed_at"] == "unknown":
            raise AssertionError(f"{report_path} reviewed evidence cannot be unknown")
        operator = report.get("run_provenance", {}).get("operator")
        if operator != "unknown" and operator == review["reviewer"]:
            raise AssertionError(f"{report_path} reviewer must differ from run operator")


def validate_benchmark_report(
    report_path: Path,
    report: dict[str, Any],
    manifest: dict[str, Any],
    run: dict[str, Any],
    task: dict[str, Any],
    *,
    require_reviewed: bool,
) -> list[str]:
    failures = validate_metrics(report, 1)
    if failures:
        raise AssertionError(f"{report_path}: {'; '.join(failures)}")
    expected = {
        "schema_version": 1,
        "report_kind": "effectiveness-benchmark-result",
        "benchmark_id": manifest["benchmark_id"],
        "task": task["name"],
        "task_id": run["task_id"],
        "task_profile": task["task_profile"],
        "adapter_mode": run["adapter_mode"],
        "operation_id": run["run_id"],
        "repetition": run["repetition"],
        "source_commit": manifest["source_commit"],
        "target_baseline_hash": run["project_baseline_hash"],
    }
    for field, value in expected.items():
        if report.get(field) != value:
            raise AssertionError(f"{report_path} field {field} does not match benchmark")
    validate_provenance(report.get("run_provenance"), report_path)
    measurement = report.get("context_measurement_kind")
    if not isinstance(measurement, str) or not measurement or is_placeholder(measurement):
        raise AssertionError(f"{report_path} context measurement kind is missing")
    for field in [
        "input_tokens",
        "output_tokens",
        "hallucinated_command_count",
        "validation_error_count",
    ]:
        value = report.get(field)
        if value != "unknown" and (not isinstance(value, int) or value < 0):
            raise AssertionError(f"{report_path} {field} must be non-negative or unknown")
    estimated_cost = report.get("estimated_cost")
    if estimated_cost != "unknown" and (
        not isinstance(estimated_cost, (int, float))
        or isinstance(estimated_cost, bool)
        or estimated_cost < 0
    ):
        raise AssertionError(
            f"{report_path} estimated_cost must be non-negative number or unknown"
        )
    for field in ["cost_currency", "cost_evidence"]:
        value = report.get(field)
        if not isinstance(value, str) or not value or is_placeholder(value):
            raise AssertionError(f"{report_path} {field} must be recorded")
    changed_files = report.get("changed_files")
    if not isinstance(changed_files, list) or not all(
        isinstance(item, str) and item and not is_placeholder(item)
        for item in changed_files
    ):
        raise AssertionError(f"{report_path} changed_files must be a string list")
    for item in changed_files:
        path = Path(item)
        if item != "none" and (path.is_absolute() or ".." in path.parts):
            raise AssertionError(f"{report_path} changed file path is unsafe: {item}")
    validate_acceptance_results(report, task, report_path)
    validate_review(report, report_path, require_reviewed=require_reviewed)
    return []


def validate_benchmark(
    manifest_path: Path,
    *,
    require_reports: bool,
    require_reviewed: bool,
) -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    reports: list[dict[str, Any]] = []
    try:
        manifest = load_json(manifest_path)
        base = manifest_path.resolve().parent
        if manifest.get("schema_version") != 1:
            raise AssertionError("benchmark schema_version must be 1")
        if manifest.get("benchmark_kind") != "alatyr-effectiveness-benchmark-plan":
            raise AssertionError("benchmark_kind is invalid")
        if manifest.get("status") != "prepared-not-executed":
            raise AssertionError("benchmark status must preserve prepared-not-executed")
        if manifest.get("execution_claimed") is not False:
            raise AssertionError("prepared benchmark must not claim execution")
        if not isinstance(manifest.get("benchmark_id"), str) or not manifest["benchmark_id"]:
            raise AssertionError("benchmark_id must be non-empty")
        if not isinstance(manifest.get("source_commit"), str) or manifest["source_commit"] in {
            "",
            "unknown",
        }:
            raise AssertionError("benchmark source_commit must identify a source revision")
        if not valid_sha256(manifest.get("input_plan_hash")):
            raise AssertionError("benchmark input_plan_hash must be sha256")
        if manifest.get("modes") != MODES:
            raise AssertionError("benchmark modes must be none, minimal, full")
        repetitions = manifest.get("repetitions")
        if not isinstance(repetitions, int) or repetitions < 1:
            raise AssertionError("benchmark repetitions must be positive")
        patterns = manifest.get("adapter_surface_patterns")
        if (
            not isinstance(patterns, list)
            or not patterns
            or not all(isinstance(item, str) and adapter_pattern_allowed(item) for item in patterns)
        ):
            raise AssertionError("benchmark adapter surface patterns are missing")
        tasks = task_index(manifest)
        expected_count = len(tasks) * len(MODES) * repetitions
        if manifest.get("expected_report_count") != expected_count:
            raise AssertionError("benchmark expected_report_count drifted")
        runs = manifest.get("runs")
        if not isinstance(runs, list) or len(runs) != expected_count:
            raise AssertionError("benchmark run count drifted")

        seen: set[tuple[str, str, int]] = set()
        seen_run_ids: set[str] = set()
        seen_workspaces: set[Path] = set()
        for run in runs:
            if not isinstance(run, dict):
                raise AssertionError("benchmark runs must be objects")
            task_id = run.get("task_id")
            mode = run.get("adapter_mode")
            repetition = run.get("repetition")
            pair = (str(task_id), str(mode), repetition)
            if task_id not in tasks or mode not in MODES:
                raise AssertionError(f"benchmark run has invalid task or mode: {pair}")
            if not isinstance(repetition, int) or not 1 <= repetition <= repetitions:
                raise AssertionError(f"benchmark run has invalid repetition: {pair}")
            if pair in seen:
                raise AssertionError(f"benchmark run is duplicated: {pair}")
            seen.add(pair)
            run_id = run.get("run_id")
            if not isinstance(run_id, str) or not run_id or run_id in seen_run_ids:
                raise AssertionError(f"benchmark run_id is invalid or duplicated: {run_id}")
            seen_run_ids.add(run_id)
            if run.get("project_baseline_hash") != tasks[task_id]["project_baseline_hash"]:
                raise AssertionError(f"benchmark run baseline drifted: {pair}")
            if run.get("snapshot_hash") != tasks[task_id]["mode_snapshot_hashes"][mode]:
                raise AssertionError(f"benchmark run snapshot drifted: {pair}")
            workspace = safe_path(base, run.get("workspace"), "workspace")
            if workspace in seen_workspaces:
                raise AssertionError(f"benchmark workspace is duplicated: {workspace}")
            seen_workspaces.add(workspace)
            target = safe_path(base, run.get("target"), "target")
            prompt = safe_path(base, run.get("prompt"), "prompt")
            report_path = safe_path(base, run.get("report"), "report")
            if target != workspace / "target" or prompt != workspace / "prompt.md" or report_path != workspace / "report.json":
                raise AssertionError(f"benchmark run paths escape their workspace: {pair}")
            if not target.is_dir() or not prompt.is_file():
                raise AssertionError(f"benchmark run workspace is incomplete: {pair}")
            if not report_path.is_file():
                if require_reports:
                    failures.append(f"benchmark report is missing: {report_path}")
                else:
                    current_hash = tree_hash(target, [])
                    if current_hash != run["snapshot_hash"]:
                        failures.append(f"prepared target drifted before execution: {target}")
                continue
            report = load_json(report_path)
            validate_benchmark_report(
                report_path,
                report,
                manifest,
                run,
                tasks[task_id],
                require_reviewed=require_reviewed,
            )
            reports.append(report)
        if len(seen) != expected_count:
            raise AssertionError("benchmark runs do not cover every pair")
        if require_reports and len(reports) != expected_count:
            failures.append(
                f"benchmark captured {len(reports)} of {expected_count} expected reports"
            )
        if require_reports and len(reports) == expected_count:
            paired: dict[tuple[str, int], list[dict[str, Any]]] = {}
            for report in reports:
                key = (report["task_id"], report["repetition"])
                paired.setdefault(key, []).append(report)
            for key, pair_reports in paired.items():
                execution_contracts = {
                    (
                        report["run_provenance"]["provider"],
                        report["run_provenance"]["product"],
                        report["run_provenance"]["model"],
                        report["run_provenance"]["version_or_date"],
                        report["run_provenance"]["execution_mode"],
                        report["context_measurement_kind"],
                    )
                    for report in pair_reports
                }
                if len(execution_contracts) != 1:
                    failures.append(
                        f"paired runs use different assistant or measurement contracts: {key}"
                    )
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        failures.append(str(exc))
    return failures, reports


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def validate_source_templates() -> list[str]:
    failures: list[str] = []
    try:
        plan = load_json(PLAN_TEMPLATE)
        report = load_json(REPORT_TEMPLATE)
        if plan.get("schema_version") != 1:
            failures.append("benchmark plan template schema_version must be 1")
        if plan.get("benchmark_kind") != "alatyr-effectiveness-benchmark-input":
            failures.append("benchmark plan template kind is invalid")
        if set(plan.get("mode_contracts", {})) != set(MODES):
            failures.append("benchmark plan template must define all mode contracts")
        patterns = plan.get("adapter_surface_patterns")
        if not isinstance(patterns, list) or not all(
            isinstance(item, str) and adapter_pattern_allowed(item) for item in patterns
        ):
            failures.append("benchmark plan template adapter patterns are missing")
        tasks = plan.get("tasks")
        if not isinstance(tasks, list) or len(tasks) != 1:
            failures.append("benchmark plan template must contain one placeholder task")
        elif set(tasks[0].get("sources", {})) != set(MODES):
            failures.append("benchmark plan placeholder task must define all mode sources")
        for field in [
            "benchmark_id",
            "task_id",
            "adapter_mode",
            "operation_id",
            "repetition",
            "source_commit",
            "target_baseline_hash",
            "run_provenance",
            "context_measurement_kind",
            "input_tokens",
            "output_tokens",
            "estimated_cost",
            "cost_currency",
            "cost_evidence",
            "changed_files",
            "acceptance_criteria_results",
            "review",
        ]:
            if field not in report:
                failures.append(f"effectiveness run report template missing {field}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
    return failures


def source_self_check() -> list[str]:
    failures = validate_source_templates()
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        snapshots = base / "snapshots"
        for mode in MODES:
            write_file(snapshots / mode / "README.md", "# Paired target\n")
            write_file(snapshots / mode / "src" / "rule.txt", "same project fact\n")
        for mode in ["minimal", "full"]:
            write_file(snapshots / mode / "AGENTS.md", f"# {mode} adapter\n")
            write_file(snapshots / mode / ".ai" / "alatyr.yaml", "schema_version: 1\n")
            write_file(
                snapshots / mode / ".ai" / "assistant" / "context-router.json",
                "{}\n",
            )
        for relpath in [
            ".ai/framework/README.md",
            ".ai/project/source-of-truth-registry.md",
            ".ai/assistant/gates/checklist.md",
        ]:
            write_file(snapshots / "full" / relpath, "# Full adapter evidence\n")

        plan = {
            "schema_version": 1,
            "benchmark_kind": "alatyr-effectiveness-benchmark-input",
            "benchmark_id": "source-contract-benchmark",
            "repetitions": 1,
            "mode_contracts": {
                "none": {
                    "required_paths": [],
                    "forbidden_paths": [".ai/alatyr.yaml"],
                },
                "minimal": {
                    "required_paths": [
                        "AGENTS.md",
                        ".ai/alatyr.yaml",
                        ".ai/assistant/context-router.json",
                    ],
                    "forbidden_paths": [],
                },
                "full": {
                    "required_paths": [
                        "AGENTS.md",
                        ".ai/alatyr.yaml",
                        ".ai/framework/README.md",
                        ".ai/project/source-of-truth-registry.md",
                        ".ai/assistant/context-router.json",
                        ".ai/assistant/gates/checklist.md",
                    ],
                    "forbidden_paths": [],
                },
            },
            "adapter_surface_patterns": [
                ".ai/**",
                "AGENTS.md",
                "AI_ASSISTANTS.md",
            ],
            "tasks": [
                {
                    "id": "paired-task",
                    "name": "Paired source contract task",
                    "task_profile": "business-change",
                    "request": "Review the same generic fact.",
                    "allowed_actions": "read-only",
                    "acceptance_criteria": ["generic fact is inspected"],
                    "sources": {
                        mode: f"snapshots/{mode}" for mode in MODES
                    },
                }
            ],
        }
        plan_path = base / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        output = base / "benchmark"
        manifest_path = prepare_benchmark(plan_path, output, overwrite=False)
        prepared_failures, _ = validate_benchmark(
            manifest_path, require_reports=False, require_reviewed=False
        )
        failures.extend(prepared_failures)
        manifest = load_json(manifest_path)
        task = manifest["tasks"][0]
        for index, run in enumerate(manifest["runs"]):
            report = load_json(REPORT_TEMPLATE)
            report.update(
                {
                    "benchmark_id": manifest["benchmark_id"],
                    "task": task["name"],
                    "task_id": run["task_id"],
                    "task_profile": task["task_profile"],
                    "adapter_mode": run["adapter_mode"],
                    "operation_id": run["run_id"],
                    "repetition": run["repetition"],
                    "source_commit": manifest["source_commit"],
                    "target_baseline_hash": run["project_baseline_hash"],
                    "run_provenance": {
                        "provider": "synthetic",
                        "product": "source-check",
                        "model": "unknown",
                        "version_or_date": "unknown",
                        "execution_mode": "manual",
                        "started_at": "unknown",
                        "completed_at": "unknown",
                        "operator": "runner",
                        "report_origin": "synthetic-source-contract",
                    },
                    "context_measurement_kind": "assistant-reported-words",
                    "input_tokens": (index + 1) * 80,
                    "output_tokens": (index + 1) * 20,
                    "estimated_cost": (index + 1) * 0.01,
                    "cost_currency": "USD",
                    "cost_evidence": "synthetic source contract",
                    "context_files_loaded": index + 1,
                    "approximate_context_volume": (index + 1) * 100,
                    "context_expansions": 0,
                    "context_receipt_reused": "no",
                    "context_budget_exceeded": "no",
                    "clarifications": 0,
                    "approvals_requested": 0,
                    "validation": "synthetic source check",
                    "hallucinated_commands": "none recorded",
                    "hallucinated_command_count": 0,
                    "validation_error_count": 0,
                    "missed_companion_updates": 0,
                    "rework_count": 0,
                    "changed_fact_count": 1,
                    "relationships_reviewed": index,
                    "companion_surfaces_checked": index,
                    "unresolved_consistency_gaps": 0,
                    "duration_seconds": (index + 1) * 10,
                    "protected_changes_blocked": 0,
                    "changed_files": ["none"],
                    "residual_risks": "synthetic source contract only",
                    "outcome": "accepted",
                    "acceptance_criteria_results": [
                        {
                            "criterion": "generic fact is inspected",
                            "status": "pass",
                            "evidence": "synthetic reviewer evidence",
                        }
                    ],
                    "review": {
                        "status": "reviewed",
                        "reviewer": "reviewer",
                        "reviewed_at": "2026-01-01T00:00:00Z",
                        "notes": "synthetic independent review",
                    },
                }
            )
            report_path = safe_path(output, run["report"], "report")
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        completed_failures, reports = validate_benchmark(
            manifest_path, require_reports=True, require_reviewed=True
        )
        failures.extend(completed_failures)
        if len(reports) != 3:
            failures.append("source benchmark should capture three paired reports")

        full_run = next(run for run in manifest["runs"] if run["adapter_mode"] == "full")
        full_report_path = safe_path(output, full_run["report"], "report")
        full_report = load_json(full_report_path)
        full_report["run_provenance"]["model"] = "different-model"
        full_report_path.write_text(
            json.dumps(full_report, indent=2) + "\n", encoding="utf-8"
        )
        if not validate_benchmark(
            manifest_path, require_reports=True, require_reviewed=True
        )[0]:
            failures.append("paired benchmark must reject assistant/model drift")
        full_report["run_provenance"]["model"] = "unknown"
        full_report_path.write_text(
            json.dumps(full_report, indent=2) + "\n", encoding="utf-8"
        )

        first_report = safe_path(output, manifest["runs"][0]["report"], "report")
        first_report.unlink()
        if not validate_benchmark(
            manifest_path, require_reports=True, require_reviewed=True
        )[0]:
            failures.append("benchmark completeness must fail when one report is missing")

        shutil.rmtree(output)
        unsafe_plan = json.loads(json.dumps(plan))
        unsafe_plan["adapter_surface_patterns"].append("src/**")
        unsafe_plan_path = base / "unsafe-plan.json"
        unsafe_plan_path.write_text(
            json.dumps(unsafe_plan, indent=2) + "\n", encoding="utf-8"
        )
        try:
            prepare_benchmark(unsafe_plan_path, output, overwrite=False)
        except ValueError:
            pass
        else:
            failures.append("benchmark preparation must reject broad project exclusions")

        write_file(snapshots / "minimal" / "src" / "rule.txt", "drifted project fact\n")
        try:
            prepare_benchmark(plan_path, output, overwrite=False)
        except ValueError:
            pass
        else:
            failures.append("benchmark preparation must reject non-adapter project drift")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate prepared or completed effectiveness benchmarks."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        help="Path to prepared benchmark.json. Omit for the source self-check.",
    )
    parser.add_argument("--require-reports", action="store_true")
    parser.add_argument("--require-reviewed", action="store_true")
    args = parser.parse_args()
    if args.require_reviewed and not args.require_reports:
        print("FAIL: --require-reviewed requires --require-reports", file=sys.stderr)
        return 1
    failures = (
        validate_benchmark(
            args.benchmark,
            require_reports=args.require_reports,
            require_reviewed=args.require_reviewed,
        )[0]
        if args.benchmark
        else source_self_check()
    )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked paired effectiveness benchmark contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
