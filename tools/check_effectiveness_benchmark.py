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

import jsonschema

from prepare_effectiveness_benchmark import (
    MODES,
    REPORT_TEMPLATE,
    adapter_pattern_allowed,
    load_json,
    prepare_benchmark,
    tree_hash,
)
from context_receipt import validate_context_receipt
from summarize_effectiveness_reports import validate_report as validate_metrics


ROOT = Path(__file__).resolve().parents[1]
PLAN_TEMPLATE = ROOT / "conformance" / "benchmarks" / "benchmark-plan-template.json"
TASK_SUITE = ROOT / "conformance" / "benchmarks" / "benchmark-task-suite.json"
DELAYED_OUTCOME_SCHEMA = ROOT / "schemas" / "alatyr-delayed-outcome-evidence.schema.json"
ADAPTER_MAINTENANCE_SCHEMA = (
    ROOT / "schemas" / "alatyr-adapter-maintenance-evidence.schema.json"
)
DELAYED_OUTCOME_TEMPLATE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "templates"
    / "delayed-outcome-evidence.json"
)
ADAPTER_MAINTENANCE_TEMPLATE = (
    ROOT
    / "templates"
    / "target"
    / ".ai"
    / "assistant"
    / "templates"
    / "adapter-maintenance-evidence.json"
)
HEX = set("0123456789abcdef")
MEASUREMENT_EVIDENCE_STATES = {"observed", "manual", "estimated", "unavailable"}
INTERVENTION_CLASSIFICATIONS = {
    "new-guidance-candidate",
    "known-guidance-routing-failure",
    "known-guidance-compliance-failure",
    "task-local",
    "scope-change",
    "validation-request",
}
CANONICAL_TASK_PROFILES = {
    "docs-local",
    "code-local",
    "business-change",
    "architecture-change",
    "data-change",
    "security-sensitive",
    "ai-infrastructure",
    "framework-upgrade",
}
QUALITY_NON_REGRESSION_METRICS = {
    "hallucinated_command_count",
    "validation_error_count",
    "missed_companion_updates",
    "rework_count",
    "unresolved_consistency_gaps",
}


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


def validate_measurement(
    value: Any,
    field: str,
    *,
    allowed_states: set[str] = MEASUREMENT_EVIDENCE_STATES,
    value_field: str = "value",
) -> None:
    if not isinstance(value, dict):
        raise AssertionError(f"{field} must be an evidence-qualified measurement")
    expected_fields = {value_field, "evidence_state", "evidence_reference"}
    if value_field == "value" and set(value) != expected_fields:
        raise AssertionError(f"{field} measurement fields drifted")
    state = value.get("evidence_state")
    if state not in allowed_states:
        raise AssertionError(f"{field} evidence_state is invalid")
    measured = value.get(value_field)
    if state == "unavailable":
        if measured != "unknown":
            raise AssertionError(f"{field} unavailable value must be unknown")
    elif not isinstance(measured, int) or isinstance(measured, bool) or measured < 0:
        raise AssertionError(f"{field} recorded value must be a non-negative integer")
    evidence = value.get("evidence_reference")
    if not isinstance(evidence, str) or not evidence or is_placeholder(evidence):
        raise AssertionError(f"{field} evidence reference or unavailable reason is missing")


def validate_measurement_evidence(value: Any, report_path: Path) -> None:
    if not isinstance(value, dict):
        raise AssertionError(f"{report_path} measurement_evidence must be an object")
    required = {
        "human_active_attention_seconds",
        "review_cycles",
        "intervention_total",
        "classified_interventions",
        "executor_active_time_seconds",
    }
    if set(value) != required:
        raise AssertionError(f"{report_path} measurement_evidence fields drifted")
    for field in [
        "human_active_attention_seconds",
        "review_cycles",
        "intervention_total",
    ]:
        validate_measurement(value[field], f"{report_path} measurement_evidence.{field}")
    validate_measurement(
        value["executor_active_time_seconds"],
        f"{report_path} measurement_evidence.executor_active_time_seconds",
        allowed_states={"observed", "unavailable"},
    )
    interventions = value["classified_interventions"]
    if not isinstance(interventions, list):
        raise AssertionError(
            f"{report_path} measurement_evidence.classified_interventions must be a list"
        )
    seen: set[str] = set()
    known_total = 0
    all_counts_known = True
    for index, intervention in enumerate(interventions):
        field = (
            f"{report_path} measurement_evidence.classified_interventions[{index}]"
        )
        if not isinstance(intervention, dict):
            raise AssertionError(f"{field} must be an object")
        if set(intervention) != {
            "classification",
            "count",
            "evidence_state",
            "evidence_reference",
        }:
            raise AssertionError(f"{field} fields drifted")
        classification = intervention.get("classification")
        if classification not in INTERVENTION_CLASSIFICATIONS:
            raise AssertionError(f"{field} classification is invalid")
        if classification in seen:
            raise AssertionError(f"{field} classification is duplicated")
        seen.add(classification)
        validate_measurement(intervention, field, value_field="count")
        count = intervention["count"]
        if isinstance(count, int) and not isinstance(count, bool):
            known_total += count
        else:
            all_counts_known = False
    total = value["intervention_total"]["value"]
    if isinstance(total, int) and not isinstance(total, bool):
        if not all_counts_known or known_total != total:
            raise AssertionError(
                f"{report_path} classified intervention counts must equal intervention_total"
            )


def measurement_contract(report: dict[str, Any]) -> tuple[Any, ...]:
    evidence = report.get("measurement_evidence", {})
    interventions = evidence.get("classified_interventions", [])
    return (
        evidence.get("human_active_attention_seconds", {}).get("evidence_state"),
        evidence.get("review_cycles", {}).get("evidence_state"),
        evidence.get("intervention_total", {}).get("evidence_state"),
        evidence.get("executor_active_time_seconds", {}).get("evidence_state"),
        tuple(
            sorted(
                (
                    item.get("classification"),
                    item.get("evidence_state"),
                )
                for item in interventions
                if isinstance(item, dict)
            )
        ),
    )


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
        class_id = task.get("class_id")
        if class_id is not None and (not isinstance(class_id, str) or not class_id):
            raise AssertionError(f"benchmark task {task_id} has invalid class_id")
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
    schema_version = report.get("schema_version")
    if schema_version not in {1, 2, 3}:
        raise AssertionError(f"{report_path} schema_version must be 1, 2, or 3")
    expected = {
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
    if schema_version in {2, 3}:
        receipt = report.get("context_receipt")
        receipt_failures = validate_context_receipt(
            receipt, f"{report_path} context_receipt"
        )
        if receipt_failures:
            raise AssertionError("; ".join(receipt_failures))
        observed = receipt["observed"]
        for report_field, receipt_field in [
            ("context_files_loaded", "files_loaded"),
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
        ]:
            receipt_value = observed[receipt_field]
            if receipt_value != "unknown" and report.get(report_field) != receipt_value:
                raise AssertionError(
                    f"{report_path} {report_field} differs from context receipt"
                )
    if schema_version == 3 and (
        "measurement_evidence" not in report or "measurement_limitations" not in report
    ):
        raise AssertionError(
            f"{report_path} schema 3 requires evidence-qualified measurements"
        )
    if "measurement_evidence" in report or "measurement_limitations" in report:
        validate_measurement_evidence(report.get("measurement_evidence"), report_path)
        limitations = report.get("measurement_limitations")
        if not isinstance(limitations, list) or not all(
            isinstance(item, str) and item and not is_placeholder(item)
            for item in limitations
        ):
            raise AssertionError(
                f"{report_path} measurement_limitations must be a string list"
            )
    if "class_id" in task:
        expected["task_class_id"] = task["class_id"]
    if "evidence_contract_digest" in manifest:
        expected["evidence_contract_digest"] = manifest["evidence_contract_digest"]
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
        if "evidence_contract_digest" in manifest and not valid_sha256(
            manifest.get("evidence_contract_digest")
        ):
            raise AssertionError("benchmark evidence_contract_digest must be sha256")
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
        suite = load_json(TASK_SUITE)
        task_classes = {
            item["id"]: item["task_profile"]
            for item in suite.get("task_classes", [])
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("task_profile"), str)
        }
        for task_id, task in tasks.items():
            class_id = task.get("class_id")
            if class_id is None:
                continue
            expected_profile = task_classes.get(class_id)
            if expected_profile is None:
                raise AssertionError(f"benchmark task {task_id} has unknown class_id")
            if task.get("task_profile") != expected_profile:
                raise AssertionError(
                    f"benchmark task {task_id} profile does not match class {class_id}"
                )
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
                        measurement_contract(report),
                    )
                    for report in pair_reports
                }
                if len(execution_contracts) != 1:
                    failures.append(
                        f"paired runs use different assistant or measurement contracts: {key}"
                    )
                by_mode = {report["adapter_mode"]: report for report in pair_reports}
                if set(by_mode) != set(MODES):
                    failures.append(f"paired runs do not cover every adapter mode: {key}")
                    continue
                reference = by_mode["none"]
                reference_acceptance = sum(
                    result.get("status") != "pass"
                    for result in reference["acceptance_criteria_results"]
                )
                for mode in ["minimal", "full"]:
                    candidate = by_mode[mode]
                    candidate_acceptance = sum(
                        result.get("status") != "pass"
                        for result in candidate["acceptance_criteria_results"]
                    )
                    if candidate_acceptance > reference_acceptance:
                        failures.append(
                            f"{mode} acceptance results regress relative to none: {key}"
                        )
                    for metric in sorted(QUALITY_NON_REGRESSION_METRICS):
                        previous = reference.get(metric)
                        current = candidate.get(metric)
                        if not isinstance(previous, int) or not isinstance(current, int):
                            failures.append(
                                f"paired quality metric {metric} is not comparable: {key}"
                            )
                        elif current > previous:
                            failures.append(
                                f"{mode} {metric} regresses relative to none: {key}"
                            )
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        failures.append(str(exc))
    return failures, reports


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def validate_evidence_record_templates() -> list[str]:
    failures: list[str] = []
    try:
        delayed_schema = load_json(DELAYED_OUTCOME_SCHEMA)
        maintenance_schema = load_json(ADAPTER_MAINTENANCE_SCHEMA)
        for path, schema in [
            (DELAYED_OUTCOME_SCHEMA, delayed_schema),
            (ADAPTER_MAINTENANCE_SCHEMA, maintenance_schema),
        ]:
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except jsonschema.SchemaError as exc:
                failures.append(f"{path} is not a valid Draft 7 schema: {exc.message}")

        delayed_template = load_json(DELAYED_OUTCOME_TEMPLATE)
        required_delayed = {
            "schema_version",
            "record_kind",
            "evidence_classification",
            "outcome_id",
            "operation_id",
            "recorded_at",
            "outcome_type",
            "source_records",
            "prior_outcome_ids",
            "outcome",
            "immutability",
            "privacy",
        }
        if set(delayed_template) != required_delayed:
            failures.append("delayed outcome evidence template fields drifted")
        if delayed_template.get("immutability") != {
            "append_only_record": True,
            "completed_source_records_modified": False,
        }:
            failures.append(
                "delayed outcome template must preserve completed source records"
            )

        maintenance_template = load_json(ADAPTER_MAINTENANCE_TEMPLATE)
        required_metrics = {
            "files_touched",
            "manual_corrections",
            "stale_claims",
            "routing_changes",
            "validation_time_seconds",
            "local_deviations",
        }
        if set(maintenance_template.get("metrics", {})) != required_metrics:
            failures.append("adapter maintenance evidence metrics drifted")

        delayed_record = {
            "schema_version": 1,
            "record_kind": "alatyr-delayed-outcome-evidence",
            "evidence_classification": "historical-record",
            "outcome_id": "outcome-1",
            "operation_id": "operation-1",
            "recorded_at": "2026-01-02T00:00:00Z",
            "outcome_type": "merge",
            "source_records": [
                {
                    "record_kind": "debug-session",
                    "record_id": "debug-1",
                    "completion_state": "completed",
                }
            ],
            "prior_outcome_ids": [],
            "outcome": {
                "summary": "The reviewed change was merged.",
                "occurred_at": "2026-01-02T00:00:00Z",
                "evidence_state": "observed",
                "evidence_references": ["pull-request:1"],
                "limitations": [],
            },
            "immutability": {
                "append_only_record": True,
                "completed_source_records_modified": False,
            },
            "privacy": {
                "raw_chat_stored": False,
                "chain_of_thought_stored": False,
                "secrets_stored": False,
            },
        }
        delayed_validator = jsonschema.Draft7Validator(delayed_schema)
        if list(delayed_validator.iter_errors(delayed_record)):
            failures.append("delayed outcome schema rejects a valid linked record")
        invalid_delayed = json.loads(json.dumps(delayed_record))
        invalid_delayed["immutability"]["completed_source_records_modified"] = True
        if not list(delayed_validator.iter_errors(invalid_delayed)):
            failures.append("delayed outcome schema permits completed-record mutation")

        observed_measurement = {
            "value": 1,
            "evidence_state": "observed",
            "evidence_reference": "synthetic source check",
        }
        maintenance_record = {
            "schema_version": 1,
            "record_kind": "alatyr-adapter-maintenance-evidence",
            "evidence_classification": "historical-record",
            "maintenance_id": "maintenance-1",
            "operation_id": "operation-1",
            "recorded_at": "2026-01-02T00:00:00Z",
            "target_revision": "revision-1",
            "maintenance_scope": "adapter-only source check",
            "metrics": {
                field: dict(observed_measurement) for field in required_metrics
            },
            "validation": {
                "status": "passed",
                "evidence": ["synthetic schema validation"],
            },
            "limitations": ["synthetic source contract only"],
        }
        maintenance_validator = jsonschema.Draft7Validator(maintenance_schema)
        if list(maintenance_validator.iter_errors(maintenance_record)):
            failures.append("adapter maintenance schema rejects a valid record")
        invalid_maintenance = json.loads(json.dumps(maintenance_record))
        invalid_maintenance["metrics"]["files_touched"] = {
            "value": 0,
            "evidence_state": "unavailable",
            "evidence_reference": "not measured",
        }
        if not list(maintenance_validator.iter_errors(invalid_maintenance)):
            failures.append(
                "adapter maintenance schema treats unavailable evidence as zero"
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
    return failures


def validate_source_templates() -> list[str]:
    failures: list[str] = []
    try:
        plan = load_json(PLAN_TEMPLATE)
        report = load_json(REPORT_TEMPLATE)
        if report.get("schema_version") != 2:
            failures.append("effectiveness run report template schema_version must be 2")
        suite = load_json(TASK_SUITE)
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
        elif "class_id" not in tasks[0]:
            failures.append("benchmark plan placeholder task must define class_id")
        for field in [
            "benchmark_id",
            "task_id",
            "task_class_id",
            "adapter_mode",
            "operation_id",
            "repetition",
            "source_commit",
            "evidence_contract_digest",
            "target_baseline_hash",
            "run_provenance",
            "context_receipt",
            "context_measurement_kind",
            "input_tokens",
            "output_tokens",
            "estimated_cost",
            "cost_currency",
            "cost_evidence",
            "measurement_evidence",
            "measurement_limitations",
            "changed_files",
            "acceptance_criteria_results",
            "review",
        ]:
            if field not in report:
                failures.append(f"effectiveness run report template missing {field}")
        if suite.get("schema_version") != 1:
            failures.append("benchmark task suite schema_version must be 1")
        if suite.get("suite_kind") != "alatyr-effectiveness-task-class-suite":
            failures.append("benchmark task suite kind is invalid")
        if suite.get("status") != "coverage-contract-not-executed":
            failures.append("benchmark task suite must not claim execution")
        if suite.get("required_adapter_modes") != MODES:
            failures.append("benchmark task suite must compare none, minimal, and full")
        repetitions = suite.get("recommended_minimum_repetitions")
        if not isinstance(repetitions, int) or repetitions < 2:
            failures.append("benchmark task suite must recommend repeated runs")
        for field in ["required_acceptance_dimensions", "required_metrics"]:
            values = suite.get(field)
            if not isinstance(values, list) or len(values) < 4 or not all(
                isinstance(value, str) and value for value in values
            ):
                failures.append(f"benchmark task suite {field} is incomplete")
        quality = suite.get("quality_non_regression")
        if not isinstance(quality, dict):
            failures.append("benchmark task suite needs a quality non-regression contract")
        else:
            if quality.get("reference_mode") != "none":
                failures.append("quality reference mode must be none")
            if quality.get("candidate_modes") != ["minimal", "full"]:
                failures.append("quality candidate modes must be minimal and full")
            metrics = quality.get("metrics_that_must_not_increase")
            if not isinstance(metrics, list) or set(metrics) != QUALITY_NON_REGRESSION_METRICS:
                failures.append("quality non-regression metrics are incomplete")
            rule = quality.get("acceptance_rule")
            if not isinstance(rule, str) or "only when" not in rule:
                failures.append("quality non-regression acceptance rule is incomplete")
        task_classes = suite.get("task_classes")
        if not isinstance(task_classes, list) or len(task_classes) < 6:
            failures.append("benchmark task suite must cover at least six task classes")
        else:
            seen_classes: set[str] = set()
            covered_profiles: set[str] = set()
            for index, task_class in enumerate(task_classes):
                if not isinstance(task_class, dict):
                    failures.append(f"benchmark task class {index} must be an object")
                    continue
                class_id = task_class.get("id")
                if not isinstance(class_id, str) or not class_id or class_id in seen_classes:
                    failures.append(f"benchmark task class {index} has invalid id")
                else:
                    seen_classes.add(class_id)
                profile = task_class.get("task_profile")
                if profile not in CANONICAL_TASK_PROFILES:
                    failures.append(f"benchmark task class {class_id} has invalid profile")
                else:
                    covered_profiles.add(profile)
                for field in ["task_scale", "risk_focus", "purpose"]:
                    value = task_class.get(field)
                    if not isinstance(value, str) or not value:
                        failures.append(f"benchmark task class {class_id} missing {field}")
            required_profiles = {
                "docs-local",
                "code-local",
                "business-change",
                "architecture-change",
                "data-change",
                "security-sensitive",
            }
            if not required_profiles <= covered_profiles:
                failures.append("benchmark task suite misses required risk profiles")
        claim_boundary = suite.get("claim_boundary")
        if not isinstance(claim_boundary, str) or "no execution results" not in claim_boundary:
            failures.append("benchmark task suite must state its non-evidence boundary")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
    failures.extend(validate_evidence_record_templates())
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
            write_file(
                snapshots / mode / ".ai" / "assistant" / "bootstrap-index.json",
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
                        ".ai/assistant/bootstrap-index.json",
                        ".ai/assistant/context-router.json",
                    ],
                    "forbidden_paths": [],
                },
                "full": {
                    "required_paths": [
                        "AGENTS.md",
                        ".ai/alatyr.yaml",
                        ".ai/assistant/bootstrap-index.json",
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
                    "class_id": "business-rule-change",
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
                    "task_class_id": task["class_id"],
                    "task_profile": task["task_profile"],
                    "adapter_mode": run["adapter_mode"],
                    "operation_id": run["run_id"],
                    "repetition": run["repetition"],
                    "source_commit": manifest["source_commit"],
                    "evidence_contract_digest": manifest["evidence_contract_digest"],
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
                    "context_receipt": {
                        "schema_version": 1,
                        "receipt_kind": "alatyr-context-receipt",
                        "measurement_state": "observed",
                        "planned": {
                            "paths": ["AGENTS.md"],
                            "approximate_words": 100,
                        },
                        "resolved": {
                            "status": "recorded",
                            "paths": ["AGENTS.md"],
                            "approximate_words": (index + 1) * 100,
                        },
                        "observed": {
                            "evidence_level": "partial",
                            "source": "assistant-reported",
                            "files_loaded": index + 1,
                            "input_tokens": (index + 1) * 80,
                            "output_tokens": (index + 1) * 20,
                            "evidence": "synthetic assistant-reported source check",
                        },
                    },
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
                    "measurement_evidence": {
                        "human_active_attention_seconds": {
                            "value": (index + 1) * 5,
                            "evidence_state": "manual",
                            "evidence_reference": "synthetic bounded review log",
                        },
                        "review_cycles": {
                            "value": 1,
                            "evidence_state": "manual",
                            "evidence_reference": "synthetic review record",
                        },
                        "intervention_total": {
                            "value": 0,
                            "evidence_state": "manual",
                            "evidence_reference": "synthetic review record",
                        },
                        "classified_interventions": [],
                        "executor_active_time_seconds": {
                            "value": "unknown",
                            "evidence_state": "unavailable",
                            "evidence_reference": "no host active-time telemetry",
                        },
                    },
                    "measurement_limitations": [
                        "synthetic source contract only"
                    ],
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

        full_report["measurement_evidence"]["executor_active_time_seconds"] = {
            "value": 12,
            "evidence_state": "estimated",
            "evidence_reference": "wall-clock estimate",
        }
        full_report_path.write_text(
            json.dumps(full_report, indent=2) + "\n", encoding="utf-8"
        )
        if not validate_benchmark(
            manifest_path, require_reports=True, require_reviewed=True
        )[0]:
            failures.append("benchmark must reject estimated executor active time")
        full_report["measurement_evidence"]["executor_active_time_seconds"] = {
            "value": "unknown",
            "evidence_state": "unavailable",
            "evidence_reference": "no host active-time telemetry",
        }
        full_report_path.write_text(
            json.dumps(full_report, indent=2) + "\n", encoding="utf-8"
        )

        original_human_attention = dict(
            full_report["measurement_evidence"]["human_active_attention_seconds"]
        )
        full_report["measurement_evidence"]["human_active_attention_seconds"] = {
            "value": 0,
            "evidence_state": "unavailable",
            "evidence_reference": "not measured",
        }
        full_report_path.write_text(
            json.dumps(full_report, indent=2) + "\n", encoding="utf-8"
        )
        if not validate_benchmark(
            manifest_path, require_reports=True, require_reviewed=True
        )[0]:
            failures.append("benchmark must not treat unavailable attention as zero")
        full_report["measurement_evidence"][
            "human_active_attention_seconds"
        ] = original_human_attention
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
