"""Read-only incident views and report deltas; never acceptance or scope waivers."""

from __future__ import annotations

from collections import Counter
from itertools import islice
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from task_evidence_contract import task_schema, task_predecessor_failures


def incident_frontier(index: Any) -> dict[str, Any]:
    if not isinstance(index, dict) or not isinstance(index.get("tasks"), list) or len(index["tasks"]) > 128:
        return {"state": "unknown", "errors": ["a bounded active-task index is required"], "frontier": [], "retained_active": []}
    declared = sorted({task["task_id"] for task in index["tasks"] if isinstance(task, dict) and task.get("state") == "active" and isinstance(task.get("task_id"), str)})
    errors = []
    for error in islice(task_schema("active-task-index").iter_errors(index), 8):
        location = ".".join(map(str, error.absolute_path)) or "root"
        detail = "invalid " + error.validator
        if error.validator == "required" and isinstance(error.instance, dict):
            detail = "missing required fields: " + ", ".join(key for key in error.validator_value if key not in error.instance)
        errors.append(location + ": " + detail)
    if errors:
        return {"state": "unknown", "errors": errors, "frontier": [], "retained_active": declared}
    tasks = index["tasks"]
    ids = [task["task_id"] for task in tasks]
    if len(set(ids)) != len(ids):
        errors.append("duplicate task IDs")
    errors.extend(task_predecessor_failures(tasks))
    active = sorted(task["task_id"] for task in tasks if task["state"] == "active")
    if errors:
        return {"state": "unknown", "errors": sorted(set(errors))[:8], "frontier": [], "retained_active": active}
    by_id = {task["task_id"]: task for task in tasks}
    predecessor_ids = set()
    for task_id in active:
        pending, visited = list(by_id[task_id]["predecessor_task_ids"]), set()
        while pending:
            predecessor = pending.pop()
            if predecessor not in visited:
                visited.add(predecessor)
                predecessor_ids.add(predecessor)
                pending.extend(by_id[predecessor]["predecessor_task_ids"])
    frontier = [task_id for task_id in active if task_id not in predecessor_ids]
    return {
        "state": "derived", "frontier": frontier, "retained_active": active,
        "active_ancestor_ids": [task_id for task_id in active if task_id in predecessor_ids],
        "declared_failed_gates": sorted({task["latest_failed_gate_id"] for task in tasks if task["latest_failed_gate_id"] != "none"}),
        "limitation": "Graph leaves are navigation, not sole actionable duties. All active ancestors and failed-gate declarations remain; headers do not prove gate resolution or common causality. Canonical validation is unchanged.",
    }


def _findings(report: Any) -> list[tuple[str, str, str | None, str]] | None:
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 3 or report.get("tool") != "validate_target_adapter":
        return None
    evidence = report.get("evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("observed_revision"), str) or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", evidence["observed_revision"]) is None:
        return None
    target = report.get("target")
    if not isinstance(target, str) or not (PurePosixPath(target).is_absolute() or PureWindowsPath(target).is_absolute()):
        return None
    if report.get("status") not in ("passed", "failed", "staged") or type(report.get("strict_warnings")) is not bool or report.get("validation_scope") not in ("full", "changed") or report.get("validation_phase") not in ("acceptance", "migration-staging"):
        return None
    findings, counts = report.get("findings"), report.get("counts")
    if not isinstance(findings, list) or len(findings) > 10000 or not isinstance(counts, dict):
        return None
    result = []
    for item in findings:
        if not isinstance(item, dict) or not isinstance(item.get("level"), str) or item["level"] not in {"error", "warning", "info"}:
            return None
        if not all(isinstance(item.get(key), str) and item[key] for key in ("code", "message")) or item.get("path") is not None and not isinstance(item["path"], str):
            return None
        result.append((item["level"], item["code"], item.get("path"), item["message"]))
    for level, key in (("error", "errors"), ("warning", "warnings"), ("info", "info")):
        if type(counts.get(key)) is not int or counts[key] != sum(item[0] == level for item in result):
            return None
    exit_code = report.get("exit_code")
    if type(exit_code) is not int or exit_code not in (0, 1):
        return None
    from validate_target_adapter import Finding, is_blocking_finding, result_code
    canonical = [Finding(level, code, message, path) for level, code, path, message in result]
    blocking_warnings = sum(item.level == "warning" and is_blocking_finding(item) for item in canonical)
    if counts["warnings"] and (type(counts.get("blocking_warnings")) is not int or counts["blocking_warnings"] != blocking_warnings):
        return None
    if any("blocking" in item and (type(item["blocking"]) is not bool or item["blocking"] != is_blocking_finding(finding)) for item, finding in zip(findings, canonical)):
        return None
    expected_exit = result_code(canonical, strict_warnings=report["strict_warnings"])
    if exit_code != expected_exit:
        return None
    expected_status = "failed" if exit_code else "staged" if report["validation_phase"] == "migration-staging" else "passed"
    if report["status"] != expected_status:
        return None
    return result


def reconcile_findings(current: Any, baseline: Any = None) -> dict[str, Any]:
    current_items, baseline_items = _findings(current), _findings(baseline)
    compatible = current_items is not None and baseline_items is not None
    keys = ("target", "validation_phase", "validation_scope", "strict_warnings", "comparison_context")
    if compatible:
        compatible = all(key in current and key in baseline and current[key] == baseline[key] for key in keys)
        archive = current.get("approval_archive")
        old_archive = baseline.get("approval_archive")
        compatible = compatible and isinstance(archive, dict) and isinstance(old_archive, dict) and archive.get("mode") in ("full", "changed") and archive["mode"] == old_archive.get("mode")
        context = current.get("comparison_context")
        compatible = compatible and isinstance(context, dict) and set(context) == {"configuration_sha256", "producer_sha256"} and all(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value) for value in context.values())
    current_counts = Counter(current_items or [])
    previous_counts = Counter(baseline_items or []) if compatible else Counter()
    entries = []
    for signature in sorted(set(current_counts) | set(previous_counts), key=lambda item: (item[0], item[1], (0, "") if item[2] is None else (1, item[2]), item[3])):
        old, new = previous_counts[signature], current_counts[signature]
        entries.append({
            "finding": dict(zip(("level", "code", "path", "message"), signature)),
            "current_count": new,
            "carried_count": min(old, new) if compatible else None,
            "introduced_count": max(0, new - old) if compatible else None,
            "not_observed_count": max(0, old - new) if compatible else None,
        })
    return {"state": "comparable" if compatible else "unknown", "entries": entries,
            "limitation": "Exact report-occurrence comparison only. Missing/incompatible baseline or context is unknown. Disappearance is not proven repair, inherited findings still block, and no approval or acceptance is granted."}
